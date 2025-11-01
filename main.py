import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import os
import re
import threading
from urllib.parse import quote, unquote
from datetime import datetime
from PIL import Image, ImageTk
import io
import pymysql
from pymysql.cursors import DictCursor

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host='192.168.31.28',
                user='root',
                password='root',
                database='animes_db',
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            print("数据库连接成功")
        except Exception as e:
            print(f"数据库连接失败: {e}")
            messagebox.showerror("数据库错误", f"无法连接数据库: {e}")
    
    def get_connection(self):
        """获取数据库连接，如果断开则重连"""
        if self.connection is None or not self.connection.open:
            self.connect()
        return self.connection
    
    def check_user_exists(self, uid=1):
        """检查用户是否存在，如果不存在则创建默认用户"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT uid FROM userinfo WHERE uid = %s", (uid,))
                result = cursor.fetchone()
                
                if not result:
                    # 创建默认用户
                    cursor.execute("""
                        INSERT INTO userinfo (tel, mail, uname, pwd, register_time) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, ('13800138000', 'default@example.com', '默认用户', '123456', datetime.now()))
                    conn.commit()
                    print("创建默认用户成功")
                    
        except Exception as e:
            print(f"检查用户失败: {e}")
    
    def anime_exists(self, title, source):
        """检查动漫是否已存在"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT aid FROM animesinfo WHERE (acn_name = %s OR ajp_name = %s) AND source = %s", 
                              (title, title, source))
                result = cursor.fetchone()
                return result['aid'] if result else None
        except Exception as e:
            print(f"检查动漫存在失败: {e}")
            return None
    
    def insert_anime(self, anime_info):
        """插入动漫信息到数据库"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # 检查是否已存在
                existing_aid = self.anime_exists(anime_info['title'], anime_info['source'])
                
                if existing_aid:
                    print(f"动漫已存在，ID: {existing_aid}")
                    return existing_aid
                
                # 解析开播时间
                broadcast_time = None
                if 'air_date' in anime_info and anime_info['air_date']:
                    try:
                        broadcast_time = datetime.strptime(anime_info['air_date'], '%Y-%m-%d')
                    except:
                        pass
                
                # 解析集数
                episodes = None
                if 'episodes' in anime_info and anime_info['episodes']:
                    try:
                        # 从字符串中提取数字
                        episodes_str = anime_info['episodes']
                        episodes_match = re.search(r'(\d+)', episodes_str)
                        if episodes_match:
                            episodes = int(episodes_match.group(1))
                    except:
                        pass
                
                # 解析评分
                score = None
                if 'rating' in anime_info and anime_info['rating']:
                    try:
                        score = float(anime_info['rating'])
                    except:
                        pass
                
                # 插入动漫信息
                sql = """
                    INSERT INTO animesinfo 
                    (acn_name, ajp_name, abroadcast_time, episodes, score, source, introduce, cover_url) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    anime_info.get('name_cn', anime_info['title']),
                    anime_info['title'],
                    broadcast_time,
                    episodes,
                    score,
                    anime_info['source'],
                    anime_info.get('summary', ''),
                    anime_info.get('cover_url', '')
                ))
                
                aid = cursor.lastrowid
                conn.commit()
                print(f"动漫信息插入成功，ID: {aid}")
                return aid
                
        except Exception as e:
            print(f"插入动漫信息失败: {e}")
            return None
    
    def add_to_category(self, aid, uid, state):
        """添加动漫到用户分类"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # 检查是否已存在相同记录
                cursor.execute("""
                    SELECT rid FROM recordinfo 
                    WHERE uid = %s AND aid = %s AND state = %s
                """, (uid, aid, state))
                existing = cursor.fetchone()
                
                if existing:
                    print(f"记录已存在，RID: {existing['rid']}")
                    return existing['rid']
                
                # 插入新记录
                cursor.execute("""
                    INSERT INTO recordinfo (uid, aid, state) 
                    VALUES (%s, %s, %s)
                """, (uid, aid, state))
                
                rid = cursor.lastrowid
                conn.commit()
                print(f"分类记录插入成功，RID: {rid}")
                return rid
                
        except Exception as e:
            print(f"添加分类失败: {e}")
            return None
    
    def get_animes_by_state(self, uid, state):
        """根据状态获取用户的动漫列表"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT a.*, r.rid, r.state 
                    FROM animesinfo a 
                    INNER JOIN recordinfo r ON a.aid = r.aid 
                    WHERE r.uid = %s AND r.state = %s 
                    ORDER BY a.acn_name
                """
                cursor.execute(sql, (uid, state))
                return cursor.fetchall()
        except Exception as e:
            print(f"获取分类动漫失败: {e}")
            return []
    
    def get_anime_by_id(self, aid):
        """根据ID获取动漫信息"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM animesinfo WHERE aid = %s", (aid,))
                return cursor.fetchone()
        except Exception as e:
            print(f"获取动漫信息失败: {e}")
            return None

class AnimeInfoDownloaderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("动漫信息下载器 - 数据库版")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")
        
        # 初始化数据库管理器
        self.db = DatabaseManager()
        self.db.check_user_exists(1)  # 使用默认用户ID=1
        
        # 初始化下载器
        self.downloader = AnimeInfoDownloader()
        
        # 存储搜索结果
        self.search_results = []
        
        # 当前显示的页面
        self.current_page = None
        
        # 创建界面
        self.create_widgets()
        
        # 默认显示主页
        self.show_home()
    
    def create_widgets(self):
        # 创建菜单栏
        self.create_menu()
        
        # 主容器 - 用于切换不同页面
        self.main_container = ttk.Frame(self.root, padding="10")
        self.main_container.pack(fill=tk.BOTH, expand=True)
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 主页菜单
        home_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="主页", menu=home_menu)
        home_menu.add_command(label="搜索动漫", command=self.show_home)
        
        # 追番中菜单
        watching_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="追番中", menu=watching_menu)
        watching_menu.add_command(label="查看追番列表", command=self.show_watching_list)
        
        # 看完了菜单
        finished_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="看完了", menu=finished_menu)
        finished_menu.add_command(label="查看已完成列表", command=self.show_finished_list)
    
    def clear_current_page(self):
        """清除当前页面"""
        if self.current_page:
            for widget in self.main_container.winfo_children():
                widget.destroy()
    
    def show_home(self):
        """显示主页（搜索界面）"""
        self.clear_current_page()
        self.current_page = "home"
        
        # 搜索区域
        search_frame = ttk.LabelFrame(self.main_container, text="搜索动漫", padding="10")
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="动漫名称:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.search_anime())
        
        self.search_button = ttk.Button(search_frame, text="搜索", command=self.search_anime)
        self.search_button.grid(row=0, column=2, padx=(0, 10))
        
        self.progress = ttk.Progressbar(search_frame, mode='indeterminate')
        self.progress.grid(row=0, column=3, sticky=tk.W+tk.E)
        
        # 搜索结果区域
        results_frame = ttk.LabelFrame(self.main_container, text="搜索结果", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建滚动框架
        self.results_canvas = tk.Canvas(results_frame, bg="white")
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.results_canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        )
        
        self.results_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.results_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定鼠标滚轮事件
        self.results_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        
        self.results_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.main_container, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)
    
    def show_watching_list(self):
        """显示追番列表"""
        self.clear_current_page()
        self.current_page = "watching"
        self._show_category_list("追番中", "watching")
    
    def show_finished_list(self):
        """显示已完成列表"""
        self.clear_current_page()
        self.current_page = "finished"
        self._show_category_list("看完了", "finished")
    
    def _show_category_list(self, category_name, state):
        """显示分类列表"""
        # 标题
        title_label = ttk.Label(self.main_container, text=f"{category_name}列表", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 创建滚动区域
        canvas = tk.Canvas(self.main_container)
        scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        scrollable_frame.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # 显示分类列表
        self._populate_category_list(scrollable_frame, state)
    
    def _populate_category_list(self, parent, state):
        """填充分类列表"""
        # 从数据库获取分类列表
        animes = self.db.get_animes_by_state(1, state)  # 使用默认用户ID=1
        
        if not animes:
            ttk.Label(parent, text="该分类中还没有动漫", foreground="gray").pack(pady=20)
            return
        
        # 显示每个动漫
        for anime in animes:
            self._create_category_item(parent, anime)
    
    def _create_category_item(self, parent, anime):
        """创建分类列表项"""
        # 创建项目框架
        item_frame = ttk.Frame(parent, relief="solid", borderwidth=1)
        item_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 左半部分 - 封面图片
        left_frame = ttk.Frame(item_frame)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 加载封面图片
        self._load_category_cover_image(left_frame, anime.get('cover_url', ''))
        
        # 右半部分 - 信息
        right_frame = ttk.Frame(item_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标题 - 中文和英文
        title_text = anime['ajp_name']
        if anime['acn_name'] and anime['acn_name'] != anime['ajp_name']:
            title_text = f"{anime['acn_name']}\n({anime['ajp_name']})"
        
        title_label = ttk.Label(right_frame, text=title_text, font=("Arial", 12, "bold"))
        title_label.pack(anchor=tk.W)
        
        # 基本信息框架
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        # 年份
        year = str(anime['abroadcast_time'].year) if anime['abroadcast_time'] else '未知年份'
        year_label = ttk.Label(info_frame, text=f"📅 {year}")
        year_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 集数
        episodes = anime['episodes'] if anime['episodes'] else '集数未知'
        episodes_label = ttk.Label(info_frame, text=f"🎞️ {episodes}")
        episodes_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 评分
        rating = anime['score'] if anime['score'] else '无评分'
        rating_label = ttk.Label(info_frame, text=f"⭐ {rating}")
        rating_label.pack(side=tk.LEFT)
        
        # 查看详情按钮
        detail_button = ttk.Button(right_frame, text="查看详情", 
                                  command=lambda aid=anime['aid']: self._show_category_detail(aid))
        detail_button.pack(anchor=tk.E, pady=5)
    
    def _load_category_cover_image(self, parent_frame, cover_url):
        """加载分类列表中的封面图片"""
        # 默认显示占位图
        placeholder = tk.Label(parent_frame, text="无封面", width=15, height=20, bg="lightgray")
        placeholder.pack()
        
        # 如果封面URL存在，加载图片
        if cover_url:
            # 在新线程中加载图片
            threading.Thread(target=self._fetch_category_cover_image, 
                           args=(parent_frame, placeholder, cover_url), daemon=True).start()
    
    def _fetch_category_cover_image(self, parent_frame, placeholder, cover_url):
        """获取分类列表中的封面图片"""
        try:
            # 从网络URL加载图片
            response = requests.get(cover_url, timeout=10)
            response.raise_for_status()
            
            image_data = response.content
            image = Image.open(io.BytesIO(image_data))
            image.thumbnail((100, 140))  # 调整大小
            photo = ImageTk.PhotoImage(image)
            
            # 在主线程中更新UI
            self.root.after(0, self._update_category_cover_image, parent_frame, placeholder, photo)
        except Exception:
            # 如果加载失败，显示错误图标
            self.root.after(0, lambda: placeholder.config(text="加载失败", bg="red"))
    
    def _update_category_cover_image(self, parent_frame, placeholder, photo):
        """更新分类列表中的封面图片"""
        placeholder.destroy()
        image_label = tk.Label(parent_frame, image=photo)
        image_label.image = photo  # 保持引用
        image_label.pack()
    
    def _show_category_detail(self, aid):
        """显示分类中动漫的详细信息"""
        # 从数据库获取动漫详情
        anime = self.db.get_anime_by_id(aid)
        if not anime:
            messagebox.showerror("错误", "找不到动漫的详细信息")
            return
        
        # 创建详细信息窗口 - 这里仍然使用新窗口，因为详细信息内容较多
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"{anime['ajp_name']} - 详细信息")
        detail_window.geometry("700x800")
        
        # 创建滚动区域
        canvas = tk.Canvas(detail_window)
        scrollbar = ttk.Scrollbar(detail_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        scrollable_frame.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # 显示详细信息
        self._populate_category_detail_frame(scrollable_frame, anime)
    
    def _populate_category_detail_frame(self, parent, anime):
        """填充分类详情框架"""
        # 顶部框架 - 标题和封面
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 左侧 - 封面图片
        left_frame = ttk.Frame(top_frame)
        left_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # 加载大封面图片
        self._load_category_large_cover_image(left_frame, anime.get('cover_url', ''))
        
        # 右侧 - 标题和基本信息
        right_frame = ttk.Frame(top_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 标题 - 中文和英文
        title_text = anime['ajp_name']
        if anime['acn_name'] and anime['acn_name'] != anime['ajp_name']:
            title_text = f"{anime['acn_name']}\n({anime['ajp_name']})"
        
        title_label = ttk.Label(right_frame, text=title_text, font=("Arial", 16, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 基本信息框架
        info_frame = ttk.LabelFrame(right_frame, text="基本信息", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        # 开播时间
        if anime['abroadcast_time']:
            date_label = ttk.Label(info_frame, text=f"开播时间: {anime['abroadcast_time'].strftime('%Y-%m-%d')}")
            date_label.pack(anchor=tk.W)
        
        # 集数
        if anime['episodes']:
            episodes_label = ttk.Label(info_frame, text=f"集数: {anime['episodes']}")
            episodes_label.pack(anchor=tk.W)
        
        # 来源
        if anime['source']:
            source_label = ttk.Label(info_frame, text=f"数据来源: {anime['source']}")
            source_label.pack(anchor=tk.W)
        
        # 评分
        if anime['score']:
            rating_label = ttk.Label(info_frame, text=f"评分: {anime['score']}")
            rating_label.pack(anchor=tk.W)
        
        # 简介
        if anime['introduce']:
            summary_frame = ttk.LabelFrame(parent, text="简介", padding="10")
            summary_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=15)
            summary_text.insert(tk.END, anime['introduce'])
            summary_text.config(state=tk.DISABLED)
            summary_text.pack(fill=tk.BOTH, expand=True)
    
    def _load_category_large_cover_image(self, parent_frame, cover_url):
        """加载分类详情中的大封面图片"""
        # 默认显示占位图
        placeholder = tk.Label(parent_frame, text="无封面", width=20, height=28, bg="lightgray")
        placeholder.pack()
        
        # 如果封面URL存在，加载图片
        if cover_url:
            # 在新线程中加载图片
            threading.Thread(target=self._fetch_category_large_cover_image, 
                           args=(parent_frame, placeholder, cover_url), daemon=True).start()
    
    def _fetch_category_large_cover_image(self, parent_frame, placeholder, cover_url):
        """获取分类详情中的大封面图片"""
        try:
            # 从网络URL加载图片
            response = requests.get(cover_url, timeout=10)
            response.raise_for_status()
            
            image_data = response.content
            image = Image.open(io.BytesIO(image_data))
            image.thumbnail((200, 280))  # 调整大小为更大的尺寸
            photo = ImageTk.PhotoImage(image)
            
            # 在主线程中更新UI
            self.root.after(0, self._update_category_large_cover_image, parent_frame, placeholder, photo)
        except Exception:
            # 如果加载失败，显示错误图标
            self.root.after(0, lambda: placeholder.config(text="加载失败", bg="red"))
    
    def _update_category_large_cover_image(self, parent_frame, placeholder, photo):
        """更新分类详情中的大封面图片"""
        placeholder.destroy()
        image_label = tk.Label(parent_frame, image=photo)
        image_label.image = photo  # 保持引用
        image_label.pack()
    
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.results_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def search_anime(self):
        anime_name = self.search_entry.get().strip()
        if not anime_name:
            messagebox.showwarning("输入错误", "请输入动漫名称")
            return
        
        # 禁用搜索按钮并启动进度条
        self.search_button.config(state="disabled")
        self.progress.start()
        self.status_var.set(f"正在搜索: {anime_name}")
        
        # 在新线程中执行搜索
        threading.Thread(target=self._perform_search, args=(anime_name,), daemon=True).start()
    
    def _perform_search(self, anime_name):
        try:
            self.search_results = self.downloader.search_anime(anime_name, max_results=10)
            
            # 在主线程中更新UI
            self.root.after(0, self._update_search_results)
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"搜索失败: {str(e)}"))
        finally:
            self.root.after(0, self._search_complete)
    
    def _search_complete(self):
        self.search_button.config(state="normal")
        self.progress.stop()
    
    def _show_error(self, message):
        messagebox.showerror("错误", message)
        self.status_var.set("搜索失败")
    
    def _update_search_results(self):
        # 清除之前的搜索结果
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.search_results:
            ttk.Label(self.scrollable_frame, text="未找到相关动漫", foreground="red").pack(pady=20)
            self.status_var.set("未找到相关动漫")
            return
        
        self.status_var.set(f"找到 {len(self.search_results)} 个结果")
        
        # 显示搜索结果
        for i, anime_info in enumerate(self.search_results):
            self._create_result_widget(anime_info, i)
    
    def _create_result_widget(self, anime_info, index):
        # 创建结果框架
        result_frame = ttk.Frame(self.scrollable_frame, relief="solid", borderwidth=1)
        result_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 左半部分 - 封面图片
        left_frame = ttk.Frame(result_frame)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 加载封面图片
        self._load_cover_image(left_frame, anime_info)
        
        # 右半部分 - 信息
        right_frame = ttk.Frame(result_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标题 - 中文和英文
        title_text = anime_info['title']
        if 'name_cn' in anime_info and anime_info['name_cn'] and anime_info['name_cn'] != anime_info['title']:
            title_text = f"{anime_info['name_cn']}\n({anime_info['title']})"
        
        title_label = ttk.Label(right_frame, text=title_text, font=("Arial", 12, "bold"))
        title_label.pack(anchor=tk.W)
        
        # 基本信息
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        # 年份
        year = anime_info.get('air_date', '未知年份').split('-')[0] if 'air_date' in anime_info else '未知年份'
        year_label = ttk.Label(info_frame, text=f"📅 {year}")
        year_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 集数
        episodes = anime_info.get('episodes', '集数未知')
        episodes_label = ttk.Label(info_frame, text=f"🎞️ {episodes}")
        episodes_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 评分
        rating = anime_info.get('rating', '无评分')
        rating_label = ttk.Label(info_frame, text=f"⭐ {rating}")
        rating_label.pack(side=tk.LEFT)
        
        # 简介（截取前100字符）
        if 'summary' in anime_info and anime_info['summary']:
            summary = anime_info['summary']
            if len(summary) > 100:
                summary = summary[:100] + "..."
            
            summary_label = ttk.Label(right_frame, text=summary, wraplength=600, justify=tk.LEFT)
            summary_label.pack(anchor=tk.W, fill=tk.X)
        
        # 按钮区域
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # 查看详情按钮
        detail_button = ttk.Button(button_frame, text="查看详情", 
                                  command=lambda idx=index: self._show_anime_details(idx))
        detail_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 追番按钮
        watching_button = ttk.Button(button_frame, text="追番", 
                                    command=lambda idx=index: self._add_to_watching(idx))
        watching_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 看完了按钮
        finished_button = ttk.Button(button_frame, text="看完了", 
                                    command=lambda idx=index: self._add_to_finished(idx))
        finished_button.pack(side=tk.LEFT)
    
    def _load_cover_image(self, parent_frame, anime_info):
        # 默认显示占位图
        placeholder = tk.Label(parent_frame, text="加载中...", width=15, height=20, bg="lightgray")
        placeholder.pack()
        
        # 在新线程中加载图片
        threading.Thread(target=self._fetch_cover_image, args=(parent_frame, placeholder, anime_info), daemon=True).start()
    
    def _fetch_cover_image(self, parent_frame, placeholder, anime_info):
        try:
            if 'cover_url' in anime_info and anime_info['cover_url']:
                response = requests.get(anime_info['cover_url'], timeout=10)
                response.raise_for_status()
                
                # 转换图片
                image_data = response.content
                image = Image.open(io.BytesIO(image_data))
                image.thumbnail((100, 140))  # 调整大小
                photo = ImageTk.PhotoImage(image)
                
                # 在主线程中更新UI
                self.root.after(0, self._update_cover_image, parent_frame, placeholder, photo)
        except Exception:
            # 如果加载失败，显示错误图标
            self.root.after(0, lambda: placeholder.config(text="加载失败", bg="red"))
    
    def _update_cover_image(self, parent_frame, placeholder, photo):
        placeholder.destroy()
        image_label = tk.Label(parent_frame, image=photo)
        image_label.image = photo  # 保持引用
        image_label.pack()
    
    def _show_anime_details(self, index):
        """显示动漫详情"""
        if 0 <= index < len(self.search_results):
            selected_anime = self.search_results[index]
            
            # 在主线程中显示详细信息
            self.root.after(0, lambda: self._show_anime_details_window(selected_anime))
    
    def _show_anime_details_window(self, anime_info):
        # 创建新窗口 - 详细信息仍然使用新窗口
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"{anime_info['title']} - 详细信息")
        detail_window.geometry("700x800")
        
        # 创建滚动区域
        canvas = tk.Canvas(detail_window)
        scrollbar = ttk.Scrollbar(detail_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        scrollable_frame.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # 显示详细信息
        self._populate_detail_frame(scrollable_frame, anime_info)
        
        # 添加操作按钮
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 追番按钮
        watching_button = ttk.Button(button_frame, text="追番", 
                                    command=lambda: self._add_to_watching_by_info(anime_info))
        watching_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 看完了按钮
        finished_button = ttk.Button(button_frame, text="看完了", 
                                    command=lambda: self._add_to_finished_by_info(anime_info))
        finished_button.pack(side=tk.LEFT)
    
    def _add_to_watching(self, index):
        """添加到追番列表"""
        if 0 <= index < len(self.search_results):
            anime_info = self.search_results[index]
            self._add_to_watching_by_info(anime_info)
    
    def _add_to_finished(self, index):
        """添加到看完了列表"""
        if 0 <= index < len(self.search_results):
            anime_info = self.search_results[index]
            self._add_to_finished_by_info(anime_info)
    
    def _add_to_watching_by_info(self, anime_info):
        """通过动漫信息添加到追番列表"""
        self._add_to_category(anime_info, "watching", "追番中")
    
    def _add_to_finished_by_info(self, anime_info):
        """通过动漫信息添加到看完了列表"""
        self._add_to_category(anime_info, "finished", "看完了")
    
    def _add_to_category(self, anime_info, state, category_name):
        """添加到指定分类"""
        try:
            self.status_var.set(f"正在添加到{category_name}: {anime_info['title']}")
            
            # 插入动漫信息到数据库
            aid = self.db.insert_anime(anime_info)
            if not aid:
                raise Exception("无法保存动漫信息到数据库")
            
            # 添加到用户分类
            rid = self.db.add_to_category(aid, 1, state)  # 使用默认用户ID=1
            if not rid:
                raise Exception("无法添加到分类")
            
            self.status_var.set(f"已添加到{category_name}: {anime_info['title']}")
            messagebox.showinfo("成功", f"已成功添加到{category_name}列表")
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"添加失败: {str(e)}"))
    
    def _populate_detail_frame(self, parent, anime_info):
        """填充详情框架"""
        # 顶部框架 - 标题和封面
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 左侧 - 封面图片
        left_frame = ttk.Frame(top_frame)
        left_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # 加载大封面图片
        self._load_large_cover_image(left_frame, anime_info)
        
        # 右侧 - 标题和基本信息
        right_frame = ttk.Frame(top_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 标题 - 中文和英文
        title_text = anime_info['title']
        if 'name_cn' in anime_info and anime_info['name_cn'] and anime_info['name_cn'] != anime_info['title']:
            title_text = f"{anime_info['name_cn']}\n({anime_info['title']})"
        
        title_label = ttk.Label(right_frame, text=title_text, font=("Arial", 16, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 基本信息框架
        info_frame = ttk.LabelFrame(right_frame, text="基本信息", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        # 数据来源
        source_label = ttk.Label(info_frame, text=f"数据来源: {anime_info.get('source', '未知')}")
        source_label.pack(anchor=tk.W)
        
        # 开播时间
        if 'air_date' in anime_info:
            date_label = ttk.Label(info_frame, text=f"开播时间: {anime_info['air_date']}")
            date_label.pack(anchor=tk.W)
        
        # 集数
        if 'episodes' in anime_info:
            episodes_label = ttk.Label(info_frame, text=f"集数: {anime_info['episodes']}")
            episodes_label.pack(anchor=tk.W)
        
        # 类型
        if 'type' in anime_info:
            type_label = ttk.Label(info_frame, text=f"类型: {anime_info['type']}")
            type_label.pack(anchor=tk.W)
        
        # 评分
        if 'rating' in anime_info:
            rating_label = ttk.Label(info_frame, text=f"评分: {anime_info['rating']}")
            rating_label.pack(anchor=tk.W)
        
        # 简介
        if 'summary' in anime_info and anime_info['summary']:
            summary_frame = ttk.LabelFrame(parent, text="简介", padding="10")
            summary_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=15)
            summary_text.insert(tk.END, anime_info['summary'])
            summary_text.config(state=tk.DISABLED)
            summary_text.pack(fill=tk.BOTH, expand=True)
    
    def _load_large_cover_image(self, parent_frame, anime_info):
        # 默认显示占位图
        placeholder = tk.Label(parent_frame, text="加载中...", width=20, height=28, bg="lightgray")
        placeholder.pack()
        
        # 在新线程中加载大图
        threading.Thread(target=self._fetch_large_cover_image, args=(parent_frame, placeholder, anime_info), daemon=True).start()
    
    def _fetch_large_cover_image(self, parent_frame, placeholder, anime_info):
        try:
            if 'cover_url' in anime_info and anime_info['cover_url']:
                response = requests.get(anime_info['cover_url'], timeout=10)
                response.raise_for_status()
                
                # 转换图片
                image_data = response.content
                image = Image.open(io.BytesIO(image_data))
                image.thumbnail((200, 280))  # 调整大小为更大的尺寸
                photo = ImageTk.PhotoImage(image)
                
                # 在主线程中更新UI
                self.root.after(0, self._update_large_cover_image, parent_frame, placeholder, photo)
        except Exception:
            # 如果加载失败，显示错误图标
            self.root.after(0, lambda: placeholder.config(text="加载失败", bg="red"))
    
    def _update_large_cover_image(self, parent_frame, placeholder, photo):
        placeholder.destroy()
        image_label = tk.Label(parent_frame, image=photo)
        image_label.image = photo  # 保持引用
        image_label.pack()
    
    def run(self):
        self.root.mainloop()


class AnimeInfoDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_bangumi(self, anime_name, max_results=5):
        """使用Bangumi（番组计划）API搜索动漫详细信息"""
        url = "https://api.bgm.tv/search/subject/" + quote(anime_name)
        params = {
            'type': 2,  # 2表示动画
            'responseGroup': 'large',
            'max_results': max_results
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if data.get('list') and len(data['list']) > 0:
                for item in data['list'][:max_results]:
                    # 获取详细信息
                    detail_url = f"https://api.bgm.tv/subject/{item['id']}"
                    detail_response = self.session.get(detail_url, params=params, timeout=10)
                    detail_response.raise_for_status()
                    detail_data = detail_response.json()
                    
                    # 解析基本信息
                    info = {
                        'title': item.get('name', ''),
                        'cover_url': item.get('images', {}).get('large', ''),
                        'source': 'Bangumi',
                        'id': item.get('id', '')
                    }
                    
                    # 添加详细信息
                    info.update(self._parse_bangumi_details(detail_data))
                    results.append(info)
                
                return results
                
        except Exception as e:
            print(f"Bangumi搜索失败: {e}")
        
        return []
    
    def _parse_bangumi_details(self, data):
        """解析Bangumi返回的详细信息"""
        details = {}
        
        # 基本信息
        details['name_cn'] = data.get('name_cn', '')
        details['name'] = data.get('name', '')
        
        # 开播时间
        if data.get('air_date'):
            details['air_date'] = data['air_date']
        
        # 集数 - 正确处理集数信息
        episodes = self._parse_episodes(data)
        details['episodes'] = episodes
        
        # 类型
        if data.get('platform'):
            details['type'] = data['platform']
        
        # 评分（只要分数，不要人数）
        if data.get('rating') and data['rating'].get('score'):
            details['rating'] = data['rating']['score']
        else:
            details['rating'] = "无评分"
        
        # 简介
        if data.get('summary'):
            # 清理简介中的HTML标签
            summary = re.sub(r'<[^>]+>', '', data['summary'])
            details['summary'] = summary.strip()
        
        return details
    
    def _parse_episodes(self, data):
        """解析集数信息，正确处理Bangumi返回的复杂数据结构"""
        # 尝试从不同字段获取集数
        if data.get('eps_count'):
            # 如果有明确的集数计数
            return f"全{data['eps_count']}话"
        elif data.get('total_episodes'):
            # 备用字段
            return f"全{data['total_episodes']}话"
        elif data.get('eps'):
            # 如果eps是数字
            if isinstance(data['eps'], int):
                return f"全{data['eps']}话"
            # 如果eps是列表，计算正片数量
            elif isinstance(data['eps'], list):
                # 计算正片数量（type=0的集数）
                main_episodes = [ep for ep in data['eps'] if ep.get('type') == 0]
                if main_episodes:
                    return f"全{len(main_episodes)}话"
                # 如果没有明确的正片，使用总集数
                else:
                    return f"全{len(data['eps'])}话"
        
        # 如果以上都没有，返回默认值
        return "集数未知"
    
    def search_anime(self, anime_name, max_results=5):
        """搜索动漫信息（仅使用Bangumi源）"""
        print(f"正在搜索: {anime_name}")
        
        print(f"正在尝试 Bangumi...")
        results = self.search_bangumi(anime_name, max_results)
        if results:
            print(f"✓ 在 Bangumi 找到 {len(results)} 个结果")
            return results
        else:
            print(f"✗ Bangumi 未找到结果")
            return []


if __name__ == "__main__":
    app = AnimeInfoDownloaderGUI()
    app.run()