import asyncio
import httpx
import re
import io
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from fontTools.ttLib import TTFont
from motor.motor_asyncio import AsyncIOMotorClient
import functools

# 强制立即刷新输出
print = functools.partial(print, flush=True)

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目配置
from app.config import settings

# ==========================================
# 0. 基础配置
# ==========================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
}

# 使用配置文件中的 MongoDB 连接
# 注意：爬虫脚本独立运行，不依赖 FastAPI app.state
client = AsyncIOMotorClient(
    settings.MONGO_URL,
    serverSelectionTimeoutMS=5000,
    directConnection=False  # 允许副本集连接
)
db = client[settings.MONGO_DB_NAME]  # 使用配置的数据库名


# ==========================================
# 1. 字体解析核心逻辑
# ==========================================
class FontDecoder:
    @staticmethod
    async def get_font_map(font_url: str):
        """下载并解析字体文件，生成 Unicode -> 数字 的映射"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(font_url)
            font = TTFont(io.BytesIO(resp.content))

        # 汽车之家的规律：通常 glyphNames 会按照特定的顺序或名称排列
        # 注意：实际开发中可能需要比对坐标，这里演示核心映射逻辑
        uni_list = font.getGlyphOrder()[1:]  # 排除第一个 .notdef
        # 建立一个基准映射（需根据实际抓取的字体手动调整一次基准）
        # 汽车之家常用的混淆字符集通常对应 0-9 加上一些中文字符
        map_dict = {}
        # 示例：假设我们通过坐标分析得出的顺序映射
        base_chars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '市']
        for i, uni in enumerate(uni_list):
            # 将 'uniE815' 转换为 Python 字符串中的 '\ue815'
            key = chr(int(uni[3:], 16))
            map_dict[key] = base_chars[i] if i < len(base_chars) else ""
        return map_dict


# ==========================================
# 2. 爬虫主逻辑
# ==========================================
class KoubeiSpider:
    def __init__(self, series_id: str):
        self.series_id = series_id
        self.base_url = f"https://k.autohome.com.cn/{series_id}/"
    
    async def _test_mongo_connection(self):
        """测试 MongoDB 连接"""
        try:
            # 只测试 admin 的 ping 命令，避免认证问题
            await client.admin.command('ping')
            print(f"[MongoDB] 连接正常")
            print(f"[MongoDB] 数据库 '{settings.MONGO_DB_NAME}' 已配置")
            
        except Exception as e:
            print(f"\n[错误] MongoDB 连接失败: {e}")
            print(f"[提示] 请检查 .env 文件中的 MONGO_URL 配置\n")
            raise

    async def fetch_page(self, page: int):
        url = f"{self.base_url}index_{page}.html" if page > 1 else self.base_url
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
                resp = await client.get(url)
                
                # 调试信息
                print(f"[调试] HTTP状态码: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"[错误] 网页访问失败，状态码: {resp.status_code}")
                    return None
                
                # 1. 提取当前页面的字体文件 URL
                font_file_match = re.search(r"url\('(//.*\.ttf)'\)", resp.text)
                if not font_file_match:
                    print(f"[警告] 未找到字体文件，网页可能已改版或无需解码")
                    print(f"[调试] 网页前500字符: {resp.text[:500]}")
                    
                    # 检查是否是客户端渲染（没有实际内容）
                    if 'kb-list-item' not in resp.text and '<div id="__next"' in resp.text:
                        print(f"[检测] 网页使用客户端渲染（React/Next.js），需要使用浏览器引擎")
                        print(f"[提示] 正在切换到 Playwright 模式...")
                        return await self._fetch_with_playwright(url, page)
                    
                    # 尝试不解码字体直接解析
                    return await self._parse_without_font(resp.text, page)
        except Exception as e:
            print(f"[错误] 抓取异常: {e}")
            return None

        font_url = "https:" + font_file_match.group(1)
        font_map = await FontDecoder.get_font_map(font_url)

        # 2. 解析页面内容
        soup = BeautifulSoup(resp.text, 'html.parser')
        reviews = soup.find_all('div', class_='mouthcon')

        parsed_data = []
        for r in reviews:
            raw_text = r.text
            # 3. 核心步骤：替换加密字符
            clean_text = "".join([font_map.get(c, c) for c in raw_text])

            # 提取清洗后的数字（例如油耗）
            fuel_match = re.search(r"油耗：([\d\.]+)", clean_text)

            data = {
                "series_id": self.series_id,
                "content": clean_text[:500],  # 存入核心文本
                "fuel_consumption": fuel_match.group(1) if fuel_match else None,
                "page": page
            }
            parsed_data.append(data)

        return parsed_data
    
    async def _fetch_with_playwright(self, url: str, page: int):
        """使用 Playwright 渲染页面获取动态内容"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print(f"[错误] Playwright 未安装！")
            print(f"[提示] 请运行: pip install playwright && playwright install chromium")
            return None
        
        print(f"[Playwright] 启动浏览器渲染...")
        
        try:
            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch(
                    headless=True,  # 无头模式
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                context = await browser.new_context(
                    user_agent=HEADERS["User-Agent"],
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page_obj = await context.new_page()
                
                try:
                    # 访问页面
                    print(f"[Playwright] 正在访问: {url}")
                    await page_obj.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # 等待内容加载（等待口碑列表出现）
                    print(f"[Playwright] 等待内容加载...")
                    await page_obj.wait_for_selector('li.kb-list-item', timeout=15000)
                    
                    # 获取页面 HTML
                    html_content = await page_obj.content()
                    
                    print(f"[Playwright] 页面渲染完成，开始解析...")
                    
                    # 解析内容
                    result = await self._parse_without_font(html_content, page)
                    
                    await browser.close()
                    return result
                    
                except Exception as e:
                    print(f"[Playwright] 页面加载失败: {e}")
                    await browser.close()
                    return None
                    
        except Exception as e:
            print(f"[Playwright] 浏览器启动失败: {e}")
            return None

    async def _parse_without_font(self, html_text: str, page: int):
        """解析新版网页结构"""
        soup = BeautifulSoup(html_text, 'html.parser')

        # 新版网页使用 <li class="kb-list-item">
        reviews = soup.find_all('li', class_='kb-list-item')

        if not reviews:
            print(f"[警告] 未找到 class='kb-list-item' 的评论容器")
            return None

        print(f"[成功] 找到 {len(reviews)} 条口碑")
        parsed_data = []

        for idx, r in enumerate(reviews, 1):
            try:
                # 1. 提取标题
                title_elem = r.find('p', class_='item-title')
                title = title_elem.text.strip() if title_elem else ""

                # 2. 提取【最满意】和【最不满意】
                content_elems = r.find_all('p', class_='item-intr')

                satisfied = ""  # 最满意
                unsatisfied = ""  # 最不满意

                for elem in content_elems:
                    text = elem.text.strip()
                    if '【最满意】' in text:
                        satisfied = text.replace('【最满意】', '').strip()
                    elif '【最不满意】' in text:
                        unsatisfied = text.replace('【最不满意】', '').strip()

                # 3. 提取用户昵称
                nick_elem = r.find('span', class_='nick-name')
                nickname = nick_elem.text.strip() if nick_elem else "匿名"

                # 4. 构建数据
                if satisfied or unsatisfied:  # 至少有一个内容才保存
                    data = {
                        "series_id": self.series_id,
                        "title": title,
                        "satisfied": satisfied[:1000] if satisfied else None,
                        "unsatisfied": unsatisfied[:1000] if unsatisfied else None,
                        "nickname": nickname,
                        "page": page,
                        "full_content": f"【最满意】{satisfied}\n【最不满意】{unsatisfied}"
                    }
                    parsed_data.append(data)
                    print(f"  [{idx}] {nickname}: {title[:30]}...")

            except Exception as e:
                print(f"[警告] 解析第 {idx} 条评论失败: {e}")
                continue

        return parsed_data if parsed_data else None

    async def run(self, total_pages: int):
        """爬取多页数据，自动去重"""
        # 测试 MongoDB 连接
        await self._test_mongo_connection()
        
        total_inserted = 0
        total_duplicates = 0
        
        for p in range(1, total_pages + 1):
            print(f"[抓取] 正在抓取第 {p} 页...")
            data = await self.fetch_page(p)
            
            if data:
                print(f"[抓取] 第 {p} 页获取到 {len(data)} 条数据")
                page_inserted = 0
                page_duplicates = 0
                
                # 逐条插入，处理去重
                for item in data:
                    try:
                        # 生成唯一标识（基于标题+满意内容的前100字符）
                        import hashlib
                        unique_str = f"{item['series_id']}_{item['title']}_{item.get('satisfied', '')[:100]}"
                        content_hash = hashlib.md5(unique_str.encode()).hexdigest()
                        item['content_hash'] = content_hash
                        
                        # 尝试插入（如果 content_hash 已存在会抛出异常）
                        await db.car_reviews_raw.insert_one(item)
                        page_inserted += 1
                        total_inserted += 1
                        
                    except Exception as e:
                        # 重复数据，跳过
                        if 'duplicate key' in str(e).lower():
                            page_duplicates += 1
                            total_duplicates += 1
                        else:
                            print(f"[错误] 插入失败: {e}")
                
                print(f"   [统计] 本页新增 {page_inserted} 条，跳过重复 {page_duplicates} 条")
            else:
                print(f"[警告] 第 {p} 页没有获取到数据")
                
            await asyncio.sleep(2)  # 礼貌爬取
        
        print(f"\n[完成] 爬取完成！总计新增 {total_inserted} 条，跳过重复 {total_duplicates} 条")
        return {"inserted": total_inserted, "duplicates": total_duplicates}


# ==========================================
# 3. 启动
# ==========================================
if __name__ == "__main__":
    spider = KoubeiSpider("3442")  # 示例：Model Y
    asyncio.run(spider.run(total_pages=5))