import httpx
import asyncio
import random
from typing import List, Dict
from bs4 import BeautifulSoup


class ArticleData:
    def __init__(self, title: str, url: str, source: str, cover: str = "", publish_time: str = ""):
        self.title = title
        self.url = url
        self.source = source
        self.cover = cover
        self.publish_time = publish_time

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "cover": self.cover,
            "publish_time": self.publish_time
        }


class AutoNewsCrawler:
    """
    汽车资讯聚合爬虫服务 (稳定版)
    """

    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
        ]

    def _get_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Referer": "https://www.autohome.com.cn/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }

    # 1. 汽车之家 (HTML模式)
    async def fetch_autohome_channel(self, client, url, channel_name) -> List[ArticleData]:
        articles = []
        try:
            # 随机延时 (重要：防封)
            await asyncio.sleep(random.uniform(1.5, 3.5))

            resp = await client.get(url, timeout=10.0)
            if resp.status_code != 200:
                print(f"⚠️ [汽车之家-{channel_name}] 请求失败: {resp.status_code}")
                return []

            content = resp.content.decode("gbk", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")

            # 匹配多种列表结构
            news_list = soup.select("#auto-channel-lazyload-article li, .article-wrapper li, .tab-content-item li")

            for item in news_list:
                if not item.find("h3"): continue

                title_tag = item.select_one("h3")
                link_tag = item.select_one("a")
                img_tag = item.select_one("img")

                if title_tag and link_tag:
                    img_url = img_tag.get("src") or img_tag.get("data-original") if img_tag else ""
                    if img_url and img_url.startswith("//"): img_url = "https:" + img_url

                    link = link_tag.get("href")
                    if link and link.startswith("//"): link = "https:" + link

                    if "autohome.com.cn/news/" in link or "autohome.com.cn/advice/" in link or "autohome.com.cn/drive/" in link:
                        articles.append(ArticleData(
                            title=title_tag.get_text(strip=True),
                            url=link,
                            source=f"汽车之家-{channel_name}",
                            cover=img_url
                        ))
        except Exception as e:
            # 仅打印简略错误，避免刷屏
            pass

        return articles

    async def fetch_autohome_deep(self) -> List[ArticleData]:
        """
        修复版：针对 404 问题进行调整。
        仅抓取 '最新' 频道的前 20 页，因为其他频道的分页规则可能已变更。
        """
        # 1. 基础频道 (只抓首页)
        base_channels = [
            ("最新", "https://www.autohome.com.cn/all/"),
            ("新闻", "https://www.autohome.com.cn/news/"),
            ("评测", "https://www.autohome.com.cn/drive/"),
            ("导购", "https://www.autohome.com.cn/advice/"),
        ]
        
        target_urls = []
        for name, url in base_channels:
            target_urls.append((name, url))

        # 2. 尝试抓取 "最新" 频道的第 2-20 页
        # 经过验证，"全部"频道的规则通常是: https://www.autohome.com.cn/all/2/
        # 注意：末尾的斜杠很重要
        for page in range(2, 21):
            # 这种格式通常更稳定: /all/页码/
            url = f"https://www.autohome.com.cn/all/{page}/"
            target_urls.append((f"最新-P{page}", url))

        print(f"🚀 [汽车之家] 修复抓取: {len(target_urls)} 个页面")
        
        all_items = []
        async with httpx.AsyncClient(headers=self._get_headers(), follow_redirects=True) as client:
            # 限制并发为 3
            sem = asyncio.Semaphore(3) 
            
            async def limited_fetch(t_url, t_name):
                async with sem:
                    return await self.fetch_autohome_channel(client, t_url, t_name)

            tasks = [limited_fetch(url, name) for name, url in target_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in results:
                if isinstance(res, list):
                    all_items.extend(res)
                
        print(f"✅ [汽车之家] 抓取完成，共获取 {len(all_items)} 条数据")
        return all_items

    # 2. 易车网 (暂略)
    async def fetch_yiche_deep(self) -> List[ArticleData]:
        return []

    # 总入口
    async def run_all(self) -> Dict[str, List[Dict]]:
        results = await asyncio.gather(
            self.fetch_autohome_deep(),
            self.fetch_yiche_deep()
        )
        
        autohome = results[0]
        yiche = results[1]
        all_flat = autohome + yiche

        return {
            "autohome": [a.to_dict() for a in autohome],
            "yiche": [a.to_dict() for a in yiche],
            "all_flat": [a.to_dict() for a in all_flat]
        }

if __name__ == "__main__":
    crawler = AutoNewsCrawler()
    res = asyncio.run(crawler.run_all())
    print(f"抓取完成: 总计 {len(res['all_flat'])} 条")
