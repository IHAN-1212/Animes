import requests
import json
import os
import re
from urllib.parse import quote, unquote

class AnimeCoverDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_bangumi(self, anime_name):
        """使用Bangumi（番组计划）API搜索动漫"""
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
                return {
                    'title': anime.get('name', ''),
                    'cover_url': anime.get('images', {}).get('large', ''),
                    'source': 'Bangumi'
                }
        except Exception as e:
            print(f"Bangumi搜索失败: {e}")
        
        return None
    
    def search_wikipedia(self, anime_name):
        """使用维基百科搜索动漫封面"""
        # 先搜索页面
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
            
            # 获取页面图片
            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'pageimages',
                'piprop': 'original',
                'pageids': page_id
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            if str(page_id) in pages:
                page = pages[str(page_id)]
                if 'original' in page.get('pageimage', {}):
                    cover_url = page['original']['source']
                    return {
                        'title': page.get('title', '').replace(' - 维基百科，自由的百科全书', ''),
                        'cover_url': cover_url,
                        'source': 'Wikipedia'
                    }
                    
        except Exception as e:
            print(f"维基百科搜索失败: {e}")
        
        return None
    
    def search_anilist_with_english(self, anime_name):
        """使用AniList搜索（尝试英文名称）"""
        url = "https://graphql.anilist.co"
        
        query = """
        query ($search: String) {
            Page (perPage: 1) {
                media (search: $search, type: ANIME) {
                    id
                    title {
                        romaji
                        english
                    }
                    coverImage {
                        extraLarge
                        large
                        medium
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
                return {
                    'title': anime['title']['english'] or anime['title']['romaji'],
                    'cover_url': anime['coverImage']['extraLarge'] or anime['coverImage']['large'],
                    'source': 'AniList'
                }
        except Exception as e:
            print(f"AniList搜索失败: {e}")
        
        return None
    
    def search_baidu_image(self, anime_name):
        """使用百度图片搜索（备选方案）"""
        search_url = f"https://image.baidu.com/search/acjson"
        params = {
            'tn': 'resultjson_com',
            'logid': '',
            'ipn': 'rj',
            'ct': '201326592',
            'is': '',
            'fp': 'result',
            'fr': '',
            'word': anime_name + ' 动漫 封面',
            'queryWord': anime_name + ' 动漫 封面',
            'cl': '2',
            'lm': '-1',
            'ie': 'utf-8',
            'oe': 'utf-8',
            'adpicid': '',
            'st': '-1',
            'z': '',
            'ic': '',
            'hd': '',
            'latest': '',
            'copyright': '',
            's': '',
            'se': '',
            'tab': '',
            'width': '',
            'height': '',
            'face': '0',
            'istype': '2',
            'qc': '',
            'nc': '1',
            'expermode': '',
            'nojc': '',
            'isAsync': '',
            'pn': '0',
            'rn': '30'
        }
        
        try:
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            # 百度返回的数据需要清理
            content = response.text
            content = re.sub(r"\\'", "'", content)
            content = re.sub(r"\\\"", "\"", content)
            content = re.sub(r"\\/", "/", content)
            
            data = json.loads(content)
            
            if data.get('data'):
                for item in data['data']:
                    if item.get('thumbURL'):
                        return {
                            'title': anime_name,
                            'cover_url': item['thumbURL'],
                            'source': 'Baidu Images'
                        }
                        
        except Exception as e:
            print(f"百度图片搜索失败: {e}")
        
        return None
    
    def download_cover(self, anime_info, download_path="."):
        """下载封面图片"""
        if not anime_info:
            return False
        
        title = anime_info['title']
        cover_url = anime_info['cover_url']
        source = anime_info['source']
        
        if not cover_url:
            print("未找到封面URL")
            return False
        
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
    
    def search_anime(self, anime_name):
        """综合搜索动漫封面"""
        print(f"正在搜索: {anime_name}")
        
        # 按顺序尝试不同的数据源
        sources = [
            ("Bangumi", self.search_bangumi),
            ("维基百科", self.search_wikipedia),
            ("AniList", lambda name: self.search_anilist_with_english(name)),
            ("百度图片", self.search_baidu_image)
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
    print("=== 动漫封面下载器 (多数据源版) ===")
    print("支持数据源: Bangumi, 维基百科, AniList, 百度图片")
    print()
    
    downloader = AnimeCoverDownloader()
    
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
            downloader.download_cover(anime_info, download_path)
        else:
            print(f"在所有数据源中都未找到名为 '{anime_name}' 的动漫")
            print("建议：")
            print("1. 检查动漫名称是否正确")
            print("2. 尝试使用日文原名或英文名")
            print("3. 确认该动漫是否有官方封面")

if __name__ == "__main__":
    main()