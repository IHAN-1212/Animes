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
    
    def search_bangumi(self, anime_name):
        """使用Bangumi（番组计划）API搜索动漫详细信息"""
        url = "https://api.bgm.tv/search/subject/" + quote(anime_name)
        params = {
            'type': 2,  # 2表示动画
            'responseGroup': 'large',
            'max_results': 5
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('list') and len(data['list']) > 0:
                anime = data['list'][0]  # 取第一个结果
                
                # 获取详细信息
                detail_url = f"https://api.bgm.tv/subject/{anime['id']}"
                detail_response = self.session.get(detail_url, params=params, timeout=10)
                detail_response.raise_for_status()
                detail_data = detail_response.json()
                
                # 解析详细信息
                info = {
                    'title': anime.get('name', ''),
                    'cover_url': anime.get('images', {}).get('large', ''),
                    'source': 'Bangumi',
                    'id': anime.get('id', '')
                }
                
                # 添加详细信息
                info.update(self._parse_bangumi_details(detail_data))
                return info
                
        except Exception as e:
            print(f"Bangumi搜索失败: {e}")
        
        return None
    
    def _parse_bangumi_details(self, data):
        """解析Bangumi返回的详细信息"""
        details = {}
        
        # 基本信息
        details['name_cn'] = data.get('name_cn', '')
        details['name'] = data.get('name', '')
        
        # 开播时间
        if data.get('air_date'):
            details['air_date'] = data['air_date']
        
        # 集数
        if data.get('eps'):
            details['episodes'] = data['eps']
        elif data.get('eps_count'):
            details['episodes'] = data['eps_count']
        
        # 类型
        if data.get('platform'):
            details['type'] = data['platform']
        
        # 评分
        if data.get('rating'):
            rating = data['rating']
            details['rating'] = {
                'score': rating.get('score', '无'),
                'count': rating.get('total', 0)
            }
        
        # 简介
        if data.get('summary'):
            # 清理简介中的HTML标签
            summary = re.sub(r'<[^>]+>', '', data['summary'])
            details['summary'] = summary.strip()
        
        # 其他信息
        details['rank'] = data.get('rank', '')
        
        return details
    
    def search_anilist(self, anime_name):
        """使用AniList搜索动漫详细信息"""
        url = "https://graphql.anilist.co"
        
        query = """
        query ($search: String) {
            Page (perPage: 1) {
                media (search: $search, type: ANIME) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    coverImage {
                        extraLarge
                        large
                        medium
                    }
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    episodes
                    duration
                    status
                    description
                    averageScore
                    popularity
                    genres
                    format
                    season
                    seasonYear
                    studios {
                        nodes {
                            name
                        }
                    }
                }
            }
        }
        """
        
        variables = {'search': anime_name}
        
        try:
            response = self.session.post(url, json={'query': query, 'variables': variables}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['data']['Page']['media']:
                anime = data['data']['Page']['media'][0]
                
                info = {
                    'title': anime['title']['english'] or anime['title']['romaji'],
                    'cover_url': anime['coverImage']['extraLarge'] or anime['coverImage']['large'],
                    'source': 'AniList',
                    'id': anime['id']
                }
                
                # 添加详细信息
                info.update(self._parse_anilist_details(anime))
                return info
                
        except Exception as e:
            print(f"AniList搜索失败: {e}")
        
        return None
    
    def _parse_anilist_details(self, data):
        """解析AniList返回的详细信息"""
        details = {}
        
        # 标题
        details['name_romaji'] = data['title'].get('romaji', '')
        details['name_english'] = data['title'].get('english', '')
        details['name_native'] = data['title'].get('native', '')
        
        # 开播时间
        start_date = data.get('startDate', {})
        if start_date.get('year'):
            details['air_date'] = f"{start_date['year']}-{start_date.get('month', '?')}-{start_date.get('day', '?')}"
        
        # 结束时间
        end_date = data.get('endDate', {})
        if end_date.get('year'):
            details['end_date'] = f"{end_date['year']}-{end_date.get('month', '?')}-{end_date.get('day', '?')}"
        
        # 集数和时长
        details['episodes'] = data.get('episodes', '未知')
        details['duration'] = data.get('duration', '未知')
        
        # 状态
        details['status'] = data.get('status', '未知')
        
        # 评分和人气
        details['rating'] = {
            'score': data.get('averageScore', '无'),
            'count': data.get('popularity', 0)
        }
        
        # 类型和流派
        details['format'] = data.get('format', '')
        details['genres'] = data.get('genres', [])
        
        # 季度信息
        if data.get('season') and data.get('seasonYear'):
            details['season'] = f"{data['season']} {data['seasonYear']}"
        
        # 制作公司
        if data.get('studios', {}).get('nodes'):
            details['studios'] = [studio['name'] for studio in data['studios']['nodes']]
        
        # 简介
        if data.get('description'):
            # 清理简介中的HTML标签
            description = re.sub(r'<[^>]+>', '', data['description'])
            details['summary'] = description.strip()
        
        return details
    
    def search_wikipedia(self, anime_name):
        """使用维基百科搜索动漫信息"""
        search_url = "https://zh.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': anime_name + ' 动画',
            'utf8': 1
        }
        
        try:
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            search_results = data.get('query', {}).get('search', [])
            if not search_results:
                return None
            
            # 获取第一个搜索结果的页面信息
            page_id = search_results[0]['pageid']
            
            # 获取页面内容
            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'extracts|pageimages|info',
                'inprop': 'url',
                'piprop': 'original',
                'exintro': 1,
                'explaintext': 1,
                'pageids': page_id
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            if str(page_id) in pages:
                page = pages[str(page_id)]
                
                info = {
                    'title': page.get('title', '').replace(' - 维基百科，自由的百科全书', ''),
                    'source': 'Wikipedia',
                    'id': page_id
                }
                
                # 封面图片
                if 'original' in page:
                    info['cover_url'] = page['original']['source']
                
                # 简介
                if 'extract' in page:
                    info['summary'] = page['extract']
                
                # 页面URL
                if 'fullurl' in page:
                    info['url'] = page['fullurl']
                
                return info
                    
        except Exception as e:
            print(f"维基百科搜索失败: {e}")
        
        return None
    
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
                if 'name_romaji' in anime_info and anime_info['name_romaji']:
                    f.write(f"日文名: {anime_info['name_romaji']}\n")
                if 'name_english' in anime_info and anime_info['name_english']:
                    f.write(f"英文名: {anime_info['name_english']}\n")
                if 'name_native' in anime_info and anime_info['name_native']:
                    f.write(f"原名: {anime_info['name_native']}\n")
                
                # 时间信息
                if 'air_date' in anime_info:
                    f.write(f"开播时间: {anime_info['air_date']}\n")
                if 'end_date' in anime_info:
                    f.write(f"结束时间: {anime_info['end_date']}\n")
                if 'season' in anime_info:
                    f.write(f"播出季度: {anime_info['season']}\n")
                
                # 集数信息
                if 'episodes' in anime_info:
                    f.write(f"集数: {anime_info['episodes']}\n")
                if 'duration' in anime_info:
                    f.write(f"单集时长: {anime_info['duration']}分钟\n")
                if 'status' in anime_info:
                    f.write(f"状态: {anime_info['status']}\n")
                
                # 类型和流派
                if 'type' in anime_info:
                    f.write(f"类型: {anime_info['type']}\n")
                if 'format' in anime_info:
                    f.write(f"格式: {anime_info['format']}\n")
                if 'genres' in anime_info and anime_info['genres']:
                    f.write(f"流派: {', '.join(anime_info['genres'])}\n")
                
                # 制作信息
                if 'studios' in anime_info and anime_info['studios']:
                    f.write(f"制作公司: {', '.join(anime_info['studios'])}\n")
                
                # 评分信息
                if 'rating' in anime_info:
                    rating = anime_info['rating']
                    f.write(f"评分: {rating.get('score', '无')}\n")
                    if 'count' in rating:
                        f.write(f"评分人数: {rating['count']}\n")
                
                # 排名信息
                if 'rank' in anime_info and anime_info['rank']:
                    f.write(f"排名: {anime_info['rank']}\n")
                
                # 简介
                if 'summary' in anime_info and anime_info['summary']:
                    f.write(f"\n【简介】\n{anime_info['summary']}\n")
                
                # 链接
                if 'url' in anime_info:
                    f.write(f"\n【相关链接】\n{anime_info['url']}\n")
                
                f.write(f"\n信息获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"信息已保存: {filepath}")
            return True
            
        except Exception as e:
            print(f"保存信息文件时出错: {e}")
            return False
    
    def display_info(self, anime_info):
        """在控制台显示动漫信息"""
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
        if 'name_romaji' in anime_info and anime_info['name_romaji']:
            print(f"🇯🇵 日文名: {anime_info['name_romaji']}")
        if 'name_english' in anime_info and anime_info['name_english']:
            print(f"🇺🇸 英文名: {anime_info['name_english']}")
        
        # 时间信息
        if 'air_date' in anime_info:
            print(f"📅 开播时间: {anime_info['air_date']}")
        if 'end_date' in anime_info:
            print(f"🏁 结束时间: {anime_info['end_date']}")
        if 'season' in anime_info:
            print(f"🍂 播出季度: {anime_info['season']}")
        
        # 集数信息
        if 'episodes' in anime_info:
            print(f"🎞️ 集数: {anime_info['episodes']}")
        if 'duration' in anime_info:
            print(f"⏱️ 单集时长: {anime_info['duration']}分钟")
        if 'status' in anime_info:
            print(f"📈 状态: {anime_info['status']}")
        
        # 类型和流派
        if 'type' in anime_info:
            print(f"🎭 类型: {anime_info['type']}")
        if 'format' in anime_info:
            print(f"📺 格式: {anime_info['format']}")
        if 'genres' in anime_info and anime_info['genres']:
            print(f"🏷️ 流派: {', '.join(anime_info['genres'])}")
        
        # 制作信息
        if 'studios' in anime_info and anime_info['studios']:
            print(f"🏢 制作公司: {', '.join(anime_info['studios'])}")
        
        # 评分信息
        if 'rating' in anime_info:
            rating = anime_info['rating']
            score = rating.get('score', '无')
            if score != '无':
                print(f"⭐ 评分: {score}/100")
            if 'count' in rating and rating['count']:
                print(f"👥 评分人数: {rating['count']}")
        
        # 排名信息
        if 'rank' in anime_info and anime_info['rank']:
            print(f"🏆 排名: {anime_info['rank']}")
        
        # 简介
        if 'summary' in anime_info and anime_info['summary']:
            # 截取前200字符显示，避免控制台输出过长
            summary = anime_info['summary']
            if len(summary) > 200:
                summary = summary[:200] + "..."
            print(f"\n📝 简介: {summary}")
        
        print(f"{'='*50}\n")
    
    def search_anime(self, anime_name):
        """综合搜索动漫信息"""
        print(f"正在搜索: {anime_name}")
        
        # 按顺序尝试不同的数据源
        sources = [
            ("Bangumi", self.search_bangumi),
            ("AniList", self.search_anilist),
            ("维基百科", self.search_wikipedia)
        ]
        
        for source_name, search_func in sources:
            print(f"正在尝试 {source_name}...")
            result = search_func(anime_name)
            if result:
                print(f"✓ 在 {source_name} 找到: {result['title']}")
                return result
            else:
                print(f"✗ {source_name} 未找到结果")
        
        return None

def main():
    print("=== 动漫信息下载器 ===")
    print("支持获取: 封面图片、开播时间、集数、评分、简介等详细信息")
    print("支持数据源: Bangumi, AniList, 维基百科")
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
        anime_info = downloader.search_anime(anime_name)
        
        if anime_info:
            # 显示信息
            downloader.display_info(anime_info)
            
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
            if 'cover_url' in anime_info and anime_info['cover_url']:
                download_cover = input("是否下载封面图片? (y/n, 默认y): ").strip().lower()
                if download_cover != 'n':
                    downloader.download_cover(anime_info, download_path)
            
            # 保存信息到文件
            save_info = input("是否保存详细信息到文件? (y/n, 默认y): ").strip().lower()
            if save_info != 'n':
                downloader.save_info_to_file(anime_info, download_path)
                
        else:
            print(f"在所有数据源中都未找到名为 '{anime_name}' 的动漫")
            print("建议：")
            print("1. 检查动漫名称是否正确")
            print("2. 尝试使用日文原名或英文名")

if __name__ == "__main__":
    main()