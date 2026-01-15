from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.services.news_crawler import AutoNewsCrawler
from app.models.Content_Resource import CMSPost, PostType
from app.database import AsyncSessionLocal
from sqlalchemy import select
import logging

logger = logging.getLogger("uvicorn")
scheduler = AsyncIOScheduler()


async def scheduled_crawl_task():
    """
    定时爬虫任务逻辑
    """
    logger.info("🕷️ [定时任务] 开始执行全网资讯抓取...")
    crawler = AutoNewsCrawler()
    try:
        crawl_result = await crawler.run_all()
        logger.info(f"📊 抓取统计: 懂车帝[{len(crawl_result['dongchedi'])}] 汽车之家[{len(crawl_result['autohome'])}] 易车[{len(crawl_result['yiche'])}]")
        all_articles = crawl_result["all_flat"]

        if not all_articles:
            logger.info("⚠️ [定时任务] 本次未抓取到数据")
            return

        new_count = 0
        admin_user_id = 1

        # 必须手动管理 Session，因为不在 Request 上下文中
        async with AsyncSessionLocal() as db:
            for item in all_articles:
                try:
                    # 去重
                    stmt = select(CMSPost).where(CMSPost.content_body == item["url"])
                    result = await db.execute(stmt)
                    if result.scalars().first():
                        continue

                    new_post = CMSPost(
                        user_id=admin_user_id,
                        title=item["title"],
                        post_type=PostType.ARTICLE,
                        cover_url=item["cover"],
                        content_body=item["url"],  # 存入现有字段
                        status=1,
                        ip_location=f"自动爬取|{item['source']}"
                    )
                    db.add(new_post)
                    new_count += 1
                except Exception as e:
                    logger.error(f"❌ 入库失败: {e}")

            await db.commit()
            logger.info(f"✅ [定时任务] 抓取完成，新增文章: {new_count} 篇")

    except Exception as e:
        logger.error(f"❌ [定时任务] 爬虫运行异常: {e}")


def start_scheduler():
    """
    启动调度器并添加任务
    """
    # 每隔 1 小时抓取一次
    scheduler.add_job(
        scheduled_crawl_task,
        # 每5秒执行一次
        trigger=IntervalTrigger(hours=12),
        id="news_crawler",
        replace_existing=True,
        max_instances=1,
        coalesce=True 
    )
    scheduler.start()
    logger.info("⏰ [系统] 定时任务调度器已启动 (周期:一个小时)")