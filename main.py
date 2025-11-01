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

class AnimeInfoDownloaderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("动漫信息下载器")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")
        
        # 创建下载目录
        self.download_path = "./anime_downloads"
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
        
        # 创建分类目录
        self.watching_path = os.path.join(self.download_path, "watching")
        self.finished_path = os.path.join(self.download_path, "finished")
        if not os.path.exists(self.watching_path):
            os.makedirs(self.watching_path)
        if not os.path.exists(self.finished_path):
            os.makedirs(self.finished_path)
        
        # 初始化下载器
        self.downloader = AnimeInfoDownloader()
        
        # 创建界面
        self.create_widgets()
        
        # 存储搜索结果
        self.search_results = []
        
    def create_widgets(self):
        # 创建菜单栏
        self.create_menu()
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 搜索区域
        search_frame = ttk.LabelFrame(main_frame, text="搜索动漫", padding="10")
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
        results_frame = ttk.LabelFrame(main_frame, text="搜索结果", padding="10")
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
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)
    
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
    
    def show_home(self):
        """显示主页（搜索界面）"""
        # 这里已经是主页，不需要额外操作
        pass
    
    def show_watching_list(self):
        """显示追番列表"""
        self._show_category_list("追番中", self.watching_path)
    
    def show_finished_list(self):
        """显示已完成列表"""
        self._show_category_list("看完了", self.finished_path)
    
    def _show_category_list(self, category_name, category_path):
        """显示分类列表"""
        # 创建新窗口
        list_window = tk.Toplevel(self.root)
        list_window.title(f"{category_name}列表")
        list_window.geometry("800x600")
        
        # 标题
        title_label = ttk.Label(list_window, text=f"{category_name}列表", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 创建滚动区域
        canvas = tk.Canvas(list_window)
        scrollbar = ttk.Scrollbar(list_window, orient="vertical", command=canvas.yview)
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
        self._populate_category_list(scrollable_frame, category_path)
    
    def _populate_category_list(self, parent, category_path):
        """填充分类列表"""
        # 获取分类目录中的所有信息文件
        info_files = [f for f in os.listdir(category_path) if f.endswith("_info.txt")]
        
        if not info_files:
            ttk.Label(parent, text="该分类中还没有动漫", foreground="gray").pack(pady=20)
            return
        
        # 显示每个动漫
        for info_file in info_files:
            self._create_category_item(parent, category_path, info_file)
    
    def _create_category_item(self, parent, category_path, info_file):
        """创建分类列表项"""
        # 读取信息文件
        info_path = os.path.join(category_path, info_file)
        with open(info_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题
        title_match = re.search(r"=== (.*?) ===", content)
        if not title_match:
            return
        
        title = title_match.group(1)
        
        # 提取其他信息
        name_cn = ""
        cn_match = re.search(r"中文名: (.*)", content)
        if cn_match:
            name_cn = cn_match.group(1)
        
        air_date = ""
        date_match = re.search(r"开播时间: (.*)", content)
        if date_match:
            air_date = date_match.group(1)
        
        episodes = ""
        episodes_match = re.search(r"集数: (.*)", content)
        if episodes_match:
            episodes = episodes_match.group(1)
        
        rating = ""
        rating_match = re.search(r"评分: (.*)", content)
        if rating_match:
            rating = rating_match.group(1)
        
        # 查找封面图片
        cover_file = info_file.replace("_info.txt", "_cover.jpg")
        cover_path = os.path.join(category_path, cover_file)
        
        # 创建项目框架
        item_frame = ttk.Frame(parent, relief="solid", borderwidth=1)
        item_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 左半部分 - 封面图片
        left_frame = ttk.Frame(item_frame)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 加载封面图片
        self._load_category_cover_image(left_frame, cover_path)
        
        # 右半部分 - 信息
        right_frame = ttk.Frame(item_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标题 - 中文和英文
        title_text = title
        if name_cn and name_cn != title:
            title_text = f"{name_cn}\n({title})"
        
        title_label = ttk.Label(right_frame, text=title_text, font=("Arial", 12, "bold"))
        title_label.pack(anchor=tk.W)
        
        # 基本信息
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        # 年份
        year = air_date.split('-')[0] if air_date else '未知年份'
        year_label = ttk.Label(info_frame, text=f"📅 {year}")
        year_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 集数
        episodes_label = ttk.Label(info_frame, text=f"🎞️ {episodes}")
        episodes_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 评分
        rating_label = ttk.Label(info_frame, text=f"⭐ {rating}")
        rating_label.pack(side=tk.LEFT)
        
        # 查看详情按钮
        detail_button = ttk.Button(right_frame, text="查看详情", 
                                  command=lambda t=title, p=category_path: self._show_category_detail(t, p))
        detail_button.pack(anchor=tk.E, pady=5)
    
    def _load_category_cover_image(self, parent_frame, cover_path):
        """加载分类列表中的封面图片"""
        # 默认显示占位图
        placeholder = tk.Label(parent_frame, text="无封面", width=15, height=20, bg="lightgray")
        placeholder.pack()
        
        # 如果封面文件存在，加载图片
        if os.path.exists(cover_path):
            # 在新线程中加载图片
            threading.Thread(target=self._fetch_category_cover_image, args=(parent_frame, placeholder, cover_path), daemon=True).start()
    
    def _fetch_category_cover_image(self, parent_frame, placeholder, cover_path):
        """获取分类列表中的封面图片"""
        try:
            # 从本地文件加载图片
            image = Image.open(cover_path)
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
    
    def _show_category_detail(self, title, category_path):
        """显示分类中动漫的详细信息"""
        # 读取信息文件
        info_path = os.path.join(category_path, f"{title}_info.txt")
        if not os.path.exists(info_path):
            messagebox.showerror("错误", f"找不到{title}的详细信息")
            return
        
        with open(info_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取信息
        name_cn = ""
        cn_match = re.search(r"中文名: (.*)", content)
        if cn_match:
            name_cn = cn_match.group(1)
        
        air_date = ""
        date_match = re.search(r"开播时间: (.*)", content)
        if date_match:
            air_date = date_match.group(1)
        
        episodes = ""
        episodes_match = re.search(r"集数: (.*)", content)
        if episodes_match:
            episodes = episodes_match.group(1)
        
        anime_type = ""
        type_match = re.search(r"类型: (.*)", content)
        if type_match:
            anime_type = type_match.group(1)
        
        rating = ""
        rating_match = re.search(r"评分: (.*)", content)
        if rating_match:
            rating = rating_match.group(1)
        
        # 提取简介
        summary = ""
        summary_match = re.search(r"【简介】\n(.*?)(?:\n【|$)", content, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        
        # 创建详细信息窗口
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"{title} - 详细信息")
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
        self._populate_category_detail_frame(scrollable_frame, title, name_cn, air_date, 
                                           episodes, anime_type, rating, summary, category_path)
    
    def _populate_category_detail_frame(self, parent, title, name_cn, air_date, episodes, 
                                      anime_type, rating, summary, category_path):
        """填充分类详情框架"""
        # 顶部框架 - 标题和封面
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 左侧 - 封面图片
        left_frame = ttk.Frame(top_frame)
        left_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # 加载大封面图片
        cover_path = os.path.join(category_path, f"{title}_cover.jpg")
        self._load_category_large_cover_image(left_frame, cover_path)
        
        # 右侧 - 标题和基本信息
        right_frame = ttk.Frame(top_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 标题 - 中文和英文
        title_text = title
        if name_cn and name_cn != title:
            title_text = f"{name_cn}\n({title})"
        
        title_label = ttk.Label(right_frame, text=title_text, font=("Arial", 16, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 基本信息框架
        info_frame = ttk.LabelFrame(right_frame, text="基本信息", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        # 开播时间
        if air_date:
            date_label = ttk.Label(info_frame, text=f"开播时间: {air_date}")
            date_label.pack(anchor=tk.W)
        
        # 集数
        if episodes:
            episodes_label = ttk.Label(info_frame, text=f"集数: {episodes}")
            episodes_label.pack(anchor=tk.W)
        
        # 类型
        if anime_type:
            type_label = ttk.Label(info_frame, text=f"类型: {anime_type}")
            type_label.pack(anchor=tk.W)
        
        # 评分
        if rating:
            rating_label = ttk.Label(info_frame, text=f"评分: {rating}")
            rating_label.pack(anchor=tk.W)
        
        # 简介
        if summary:
            summary_frame = ttk.LabelFrame(parent, text="简介", padding="10")
            summary_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=15)
            summary_text.insert(tk.END, summary)
            summary_text.config(state=tk.DISABLED)
            summary_text.pack(fill=tk.BOTH, expand=True)
    
    def _load_category_large_cover_image(self, parent_frame, cover_path):
        """加载分类详情中的大封面图片"""
        # 默认显示占位图
        placeholder = tk.Label(parent_frame, text="无封面", width=20, height=28, bg="lightgray")
        placeholder.pack()
        
        # 如果封面文件存在，加载图片
        if os.path.exists(cover_path):
            # 在新线程中加载图片
            threading.Thread(target=self._fetch_category_large_cover_image, 
                           args=(parent_frame, placeholder, cover_path), daemon=True).start()
    
    def _fetch_category_large_cover_image(self, parent_frame, placeholder, cover_path):
        """获取分类详情中的大封面图片"""
        try:
            # 从本地文件加载图片
            image = Image.open(cover_path)
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
        """显示动漫详情（不自动下载）"""
        if 0 <= index < len(self.search_results):
            selected_anime = self.search_results[index]
            
            # 在主线程中显示详细信息
            self.root.after(0, lambda: self._show_anime_details_window(selected_anime))
    
    def _show_anime_details_window(self, anime_info):
        # 创建新窗口
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
        self._add_to_category(anime_info, self.watching_path, "追番中")
    
    def _add_to_finished_by_info(self, anime_info):
        """通过动漫信息添加到看完了列表"""
        self._add_to_category(anime_info, self.finished_path, "看完了")
    
    def _add_to_category(self, anime_info, category_path, category_name):
        """添加到指定分类"""
        try:
            self.status_var.set(f"正在添加到{category_name}: {anime_info['title']}")
            
            # 下载封面
            if 'cover_url' in anime_info and anime_info['cover_url']:
                self.downloader.download_cover(anime_info, category_path)
            
            # 保存信息到文件
            self.downloader.save_info_to_file(anime_info, category_path)
            
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
    
    def download_cover(self, anime_info, download_path="."):
        """下载封面图片"""
        if not anime_info or 'cover_url' not in anime_info:
            print("未找到封面URL")
            return False
        
        title = anime_info['title']
        cover_url = anime_info['cover_url']
        source = anime_info['source']
        
        # 清理文件名
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = f"{safe_title}_cover.jpg"
        filepath = os.path.join(download_path, filename)
        
        try:
            print(f"正在从 {source} 下载封面: {title}")
            response = self.session.get(cover_url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"封面已下载: {filepath}")
            return True
            
        except Exception as e:
            print(f"下载封面时出错: {e}")
            return False
    
    def save_info_to_file(self, anime_info, download_path="."):
        """保存动漫信息到文本文件"""
        if not anime_info:
            return False
        
        title = anime_info['title']
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = f"{safe_title}_info.txt"
        filepath = os.path.join(download_path, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"=== {title} 详细信息 ===\n")
                f.write(f"数据来源: {anime_info.get('source', '未知')}\n")
                f.write(f"ID: {anime_info.get('id', '未知')}\n\n")
                
                # 基本信息
                f.write("【基本信息】\n")
                if 'name_cn' in anime_info and anime_info['name_cn']:
                    f.write(f"中文名: {anime_info['name_cn']}\n")
                f.write(f"标题: {title}\n")
                
                # 时间信息
                if 'air_date' in anime_info:
                    f.write(f"开播时间: {anime_info['air_date']}\n")
                
                # 集数信息
                if 'episodes' in anime_info:
                    f.write(f"集数: {anime_info['episodes']}\n")
                
                # 类型
                if 'type' in anime_info:
                    f.write(f"类型: {anime_info['type']}\n")
                
                # 评分信息
                if 'rating' in anime_info:
                    f.write(f"评分: {anime_info['rating']}\n")
                
                # 简介
                if 'summary' in anime_info and anime_info['summary']:
                    f.write(f"\n【简介】\n{anime_info['summary']}\n")
                
                f.write(f"\n信息获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"信息已保存: {filepath}")
            return True
            
        except Exception as e:
            print(f"保存信息文件时出错: {e}")
            return False
    
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