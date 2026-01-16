"""
定时爬虫调度器 - 使用 APScheduler
每 10 分钟自动爬取一次，带去重功能
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from motor.motor_asyncio import AsyncIOMotorClient

# 强制立即刷新输出（Windows 兼容）
import functools
print = functools.partial(print, flush=True)

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from scripts.web_crawler import KoubeiSpider

class ScheduledCrawler:
    """定时爬虫管理器"""
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.spider_configs = [
            {"series_id": "3442", "pages": 3},  # Model Y
            {"series_id": "4685", "pages": 3},  # 理想 L9
            # 可以添加更多车型
        ]
        
        # MongoDB 连接（用于统计）
        self.client = AsyncIOMotorClient(
            settings.MONGO_URL,
            serverSelectionTimeoutMS=5000,
            directConnection=False  # 允许副本集连接
        )
        self.db = self.client[settings.MONGO_DB_NAME]
        self._db_initialized = False
    
    async def _ensure_db_initialized(self):
        """确保数据库和索引已初始化"""
        if self._db_initialized:
            return
        
        try:
            print(f"\n[初始化] 检查 MongoDB 连接...")
            
            # 只测试 ping，不列出集合（避免 Motor 事件循环问题）
            await self.client.admin.command('ping')
            print(f"[初始化] MongoDB 连接成功")
            
            # 直接尝试创建索引（如果集合不存在会自动创建）
            print(f"[初始化] 创建索引...")
            collection_name = "car_reviews_raw"
            collection = self.db[collection_name]
            
            # 创建唯一索引（防止重复）- 如果已存在会忽略
            try:
                await collection.create_index(
                    [("content_hash", 1)],
                    unique=True,
                    name="idx_content_hash_unique",
                    background=True
                )
                print(f"[初始化] content_hash 唯一索引已创建")
            except Exception:
                print(f"[初始化] content_hash 索引已存在")
            
            # 创建 series_id 索引
            try:
                await collection.create_index(
                    [("series_id", 1)],
                    name="idx_series_id",
                    background=True
                )
                print(f"[初始化] series_id 索引已创建")
            except Exception:
                print(f"[初始化] series_id 索引已存在")
            
            self._db_initialized = True
            print(f"[初始化] 数据库初始化完成\n")
            
        except Exception as e:
            print(f"\n[错误] MongoDB 初始化失败: {e}")
            print(f"[错误] 请检查 .env 配置:")
            print(f"  MONGO_URL: 需要包含 mongodb://用户名:密码@地址:端口/?authSource=admin")
            print(f"  MONGO_DB_NAME: {settings.MONGO_DB_NAME}\n")
            raise
    
    async def crawl_task(self):
        """单次爬取任务"""
        # 确保数据库已初始化
        await self._ensure_db_initialized()
        
        start_time = datetime.now()
        print("\n" + "=" * 80)
        print(f"  定时爬取任务开始")
        print("=" * 80)
        print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"爬取车型数: {len(self.spider_configs)}")
        print("-" * 80 + "\n")
        
        total_new = 0
        
        for config in self.spider_configs:
            series_id = config["series_id"]
            pages = config["pages"]
            
            print(f"[车型 {series_id}] 开始爬取 {pages} 页...")
            
            try:
                # 执行爬取
                spider = KoubeiSpider(series_id)
                result = await spider.run(total_pages=pages)
                
                # 从返回值获取统计信息
                if result:
                    new_count = result.get("inserted", 0)
                    dup_count = result.get("duplicates", 0)
                    total_new += new_count
                    
                    print(f"[车型 {series_id}] 完成！新增 {new_count} 条，跳过重复 {dup_count} 条\n")
                else:
                    print(f"[车型 {series_id}] 完成！无数据\n")
                
            except Exception as e:
                print(f"[车型 {series_id}] [失败] 爬取失败: {e}\n")
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print("-" * 80)
        print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"耗时: {elapsed:.1f} 秒")
        print(f"本次新增: {total_new} 条数据")
        print("=" * 80 + "\n")
    
    def start(self, interval_minutes: int = 10):
        """
        启动定时调度器
        
        Args:
            interval_minutes: 爬取间隔（分钟），默认 10 分钟
        """
        print("=" * 80)
        print("  定时爬虫调度器")
        print("=" * 80)
        print(f"爬取间隔: 每 {interval_minutes} 分钟")
        print(f"监控车型: {[c['series_id'] for c in self.spider_configs]}")
        print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")
        
        # 添加定时任务
        self.scheduler.add_job(
            self.crawl_task,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='crawler_job',
            name='定时爬取任务',
            replace_existing=True,
            max_instances=1  # 防止任务重叠
        )
        
        # 立即执行一次
        print("[定时] 立即执行首次爬取...\n")
        self.scheduler.add_job(
            self.crawl_task,
            id='crawler_job_immediate',
            name='立即执行'
        )
        
        # 启动调度器
        self.scheduler.start()
        
        print(f"[成功] 调度器已启动！按 Ctrl+C 停止\n")
        
        try:
            # 保持运行
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            print("\n\n正在停止调度器...")
            self.scheduler.shutdown()
            self.client.close()
            print("[完成] 调度器已停止")


# ==========================================
# 命令行启动
# ==========================================
if __name__ == "__main__":
    import argparse
    
    # 创建命令行参数解析器，用于解析定时爬虫调度器的配置参数
    parser = argparse.ArgumentParser(description='定时爬虫调度器')
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='爬取间隔（分钟），默认 10 分钟'
    )
    parser.add_argument(
        '--series',
        type=str,
        nargs='+',
        help='要爬取的车型 ID，多个用空格分隔'
    )

    args = parser.parse_args()

    crawler = ScheduledCrawler()

    # 如果用户通过命令行指定了车型 ID，则使用指定的车型 ID 覆盖默认的爬虫配置
    if args.series:
        crawler.spider_configs = [
            {"series_id": sid, "pages": 3} for sid in args.series
        ]

    # 启动定时爬虫，使用指定的时间间隔（分钟）作为参数
    crawler.start(interval_minutes=args.interval)

