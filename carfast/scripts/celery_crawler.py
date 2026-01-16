"""
Celery 定时爬虫任务
适合生产环境，支持分布式、任务队列、失败重试等
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from celery import Celery
from motor.motor_asyncio import AsyncIOMotorClient

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from scripts.web_crawler import KoubeiSpider


# ==========================================
# 初始化 Celery
# ==========================================
app = Celery(
    'crawler_tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery 配置
app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 分钟超时
    task_soft_time_limit=25 * 60,  # 25 分钟软超时
)

# 定时任务配置
app.conf.beat_schedule = {
    'crawl-every-10-minutes': {
        'task': 'scripts.celery_crawler.crawl_all_series',
        'schedule': 600.0,  # 每 10 分钟 (600 秒)
        'options': {'queue': 'crawler'},
    },
}


# ==========================================
# Celery 任务定义
# ==========================================
@app.task(bind=True, name='scripts.celery_crawler.crawl_series')
def crawl_series(self, series_id: str, total_pages: int = 3):
    """
    爬取单个车型的任务
    
    Args:
        series_id: 车型 ID
        total_pages: 爬取页数
    """
    print(f"[Celery 任务] 开始爬取车型 {series_id}")
    
    try:
        # 在 Celery Worker 中运行异步任务
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 执行爬取
        spider = KoubeiSpider(series_id)
        loop.run_until_complete(spider.run(total_pages=total_pages))
        
        return {
            'status': 'success',
            'series_id': series_id,
            'pages': total_pages,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[Celery 任务] ❌ 爬取失败: {e}")
        # 重试机制
        raise self.retry(exc=e, countdown=300, max_retries=3)


@app.task(name='scripts.celery_crawler.crawl_all_series')
def crawl_all_series():
    """
    爬取所有配置的车型（定时任务入口）
    """
    print("\n" + "=" * 60)
    print("  [Celery Beat] 定时爬取任务触发")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 配置要爬取的车型
    series_configs = [
        {"series_id": "3442", "pages": 3},  # Model Y
        {"series_id": "4685", "pages": 3},  # 理想 L9
    ]
    
    # 为每个车型创建子任务
    for config in series_configs:
        crawl_series.apply_async(
            kwargs=config,
            queue='crawler'
        )
    
    return {
        'status': 'dispatched',
        'total_tasks': len(series_configs),
        'timestamp': datetime.now().isoformat()
    }


# ==========================================
# 命令行工具
# ==========================================
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'worker':
            # 启动 Worker
            print("启动 Celery Worker...")
            app.worker_main([
                'worker',
                '--loglevel=info',
                '--queues=crawler',
                '--concurrency=2'
            ])
            
        elif command == 'beat':
            # 启动 Beat（定时任务调度器）
            print("启动 Celery Beat...")
            app.worker_main([
                'beat',
                '--loglevel=info'
            ])
            
        elif command == 'flower':
            # 启动 Flower（监控界面）
            print("启动 Flower 监控...")
            import os
            os.system(f'celery -A scripts.celery_crawler flower --port=5555')
            
        else:
            print("未知命令，支持: worker, beat, flower")
    else:
        print("用法:")
        print("  python scripts/celery_crawler.py worker  # 启动 Worker")
        print("  python scripts/celery_crawler.py beat    # 启动定时调度器")
        print("  python scripts/celery_crawler.py flower  # 启动监控界面")
