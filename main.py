import requests
import json
import os
import re
from urllib.parse import quote, unquote
from datetime import datetime

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
        
        # 集数 - 格式化为"全xx话"
        episodes = data.get('eps') or data.get('eps_count')
        if episodes:
            details['episodes'] = f"全{episodes}话"
        else:
            details['episodes'] = "集数未知"
        
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
    
    def display_brief_info(self, anime_info, index, total):
        """显示动漫的简要信息（用于列表显示）"""
        title = anime_info['title']
        
        # 获取年份和集数信息
        year = anime_info.get('air_date', '未知年份').split('-')[0] if 'air_date' in anime_info else '未知年份'
        episodes = anime_info.get('episodes', '集数未知')
        
        # 获取评分
        rating = anime_info.get('rating', '无评分')
        
        # 显示简要信息
        print(f"{index+1}. {title}")
        print(f"   📅 {year} | 🎞️ {episodes} | ⭐ {rating}")
        
        # 如果有其他名称，显示
        if 'name_cn' in anime_info and anime_info['name_cn'] and anime_info['name_cn'] != title:
            print(f"   中文名: {anime_info['name_cn']}")
        
        # 显示简介的前50个字符
        if 'summary' in anime_info and anime_info['summary']:
            summary = anime_info['summary']
            if len(summary) > 80:
                summary = summary[:80] + "..."
            print(f"   📝 {summary}")
        
        print()  # 空行分隔
    
    def display_detailed_info(self, anime_info):
        """在控制台显示动漫详细信息"""
        if not anime_info:
            return
        
        title = anime_info['title']
        source = anime_info.get('source', '未知')
        
        print(f"\n{'='*50}")
        print(f"🎬 {title}")
        print(f"{'='*50}")
        print(f"📊 数据来源: {source}")
        
        # 基本信息
        if 'name_cn' in anime_info and anime_info['name_cn']:
            print(f"🇨🇳 中文名: {anime_info['name_cn']}")
        
        # 时间信息
        if 'air_date' in anime_info:
            print(f"📅 开播时间: {anime_info['air_date']}")
        
        # 集数信息
        if 'episodes' in anime_info:
            print(f"🎞️ 集数: {anime_info['episodes']}")
        
        # 类型
        if 'type' in anime_info:
            print(f"🎭 类型: {anime_info['type']}")
        
        # 评分信息
        if 'rating' in anime_info:
            print(f"⭐ 评分: {anime_info['rating']}")
        
        # 简介
        if 'summary' in anime_info and anime_info['summary']:
            print(f"\n📝 简介:\n{anime_info['summary']}")
        
        print(f"{'='*50}\n")
    
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
    
    def select_anime(self, anime_list):
        """让用户从动漫列表中选择一个"""
        if not anime_list:
            return None
        
        print(f"\n找到 {len(anime_list)} 个相关动漫:")
        print("=" * 60)
        
        for i, anime in enumerate(anime_list):
            self.display_brief_info(anime, i, len(anime_list))
        
        while True:
            try:
                choice = input(f"请选择要查看详细信息的动漫 (1-{len(anime_list)})，或输入 'q' 退出: ").strip()
                
                if choice.lower() in ['q', 'quit', 'exit']:
                    return None
                
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(anime_list):
                        return anime_list[index]
                    else:
                        print(f"请输入 1 到 {len(anime_list)} 之间的数字")
                else:
                    print("请输入有效的数字")
                    
            except KeyboardInterrupt:
                print("\n用户中断操作")
                return None
            except Exception as e:
                print(f"输入错误: {e}")

def main():
    print("=== 动漫信息下载器 ===")
    print("数据源: Bangumi")
    print()
    
    downloader = AnimeInfoDownloader()
    
    while True:
        anime_name = input("\n请输入动漫名称 (输入 'quit' 退出): ").strip()
        
        if anime_name.lower() in ['quit', 'exit', '退出']:
            break
            
        if not anime_name:
            print("请输入有效的动漫名称")
            continue
        
        # 搜索动漫
        anime_list = downloader.search_anime(anime_name, max_results=5)
        
        if anime_list:
            # 让用户选择
            selected_anime = downloader.select_anime(anime_list)
            
            if selected_anime:
                # 显示详细信息
                downloader.display_detailed_info(selected_anime)
                
                # 询问下载路径
                download_path = input("请输入下载路径 (直接回车使用当前目录): ").strip()
                if not download_path:
                    download_path = "."
                
                # 确保目录存在
                if not os.path.exists(download_path):
                    try:
                        os.makedirs(download_path)
                    except OSError as e:
                        print(f"创建目录失败: {e}")
                        download_path = "."
                
                # 下载封面
                if 'cover_url' in selected_anime and selected_anime['cover_url']:
                    download_cover = input("是否下载封面图片? (y/n, 默认y): ").strip().lower()
                    if download_cover != 'n':
                        downloader.download_cover(selected_anime, download_path)
                
                # 保存信息到文件
                save_info = input("是否保存详细信息到文件? (y/n, 默认y): ").strip().lower()
                if save_info != 'n':
                    downloader.save_info_to_file(selected_anime, download_path)
                    
        else:
            print(f"在Bangumi中未找到名为 '{anime_name}' 的动漫")
            print("建议：")
            print("1. 检查动漫名称是否正确")
            print("2. 尝试使用日文原名")

if __name__ == "__main__":
    main()