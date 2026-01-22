from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.services.news_crawler import AutoNewsCrawler
from app.models.Content_Resource import CMSPost, PostType
from app.core.database import AsyncSessionLocal
from app.models.user import UserAuth
from sqlalchemy import select
import logging

logger = logging.getLogger("uvicorn")
scheduler = AsyncIOScheduler()


async def scheduled_crawl_task():
    """
    定时爬虫任务逻辑 (增强健壮性版)
    同步了 admin_tool.py 中的字段截断和逐条提交逻辑
    """
    logger.info("🕷️ [定时任务] 开始执行全网资讯抓取...")
    crawler = AutoNewsCrawler()
    try:
        # 1. 爬取
        crawl_result = await crawler.run_all()
        all_articles = crawl_result["all_flat"]

        if not all_articles:
            logger.info("⚠️ [定时任务] 本次未抓取到数据")
            return

        # 2. 入库
        async with AsyncSessionLocal() as db:

            # --- 用户自动修正逻辑 ---
            # 必须确保有管理员用户，否则入库会报外键错误
            admin_user = await db.get(UserAuth, 1)
            if not admin_user:
                logger.warning("⚠️ [定时任务] 管理员(ID=1)不存在，尝试创建...")
                try:
                    admin_user = UserAuth(id=1, phone="13800000000", status=1)
                    db.add(admin_user)
                    await db.flush()
                except Exception:
                    await db.rollback()
                    # 尝试获取任意一个用户作为兜底
                    stmt = select(UserAuth).limit(1)
                    res = await db.execute(stmt)
                    admin_user = res.scalars().first()

            if not admin_user:
                logger.error("❌ [定时任务] 严重错误：数据库无任何用户，无法归档文章！")
                return

            admin_user_id = admin_user.id
            new_count = 0

            for item in all_articles:
                try:
                    # 去重检查
                    stmt = select(CMSPost).where(CMSPost.content_body == item["url"])
                    result = await db.execute(stmt)
                    if result.scalars().first():
                        continue

                    # === 关键修复：字段安全截断 ===
                    safe_title = item["title"][:99] if item["title"] else "无标题"
                    safe_cover = item["cover"][:254] if item["cover"] else ""

                    new_post = CMSPost(
                        user_id=admin_user_id,
                        title=safe_title,
                        post_type=PostType.ARTICLE,
                        cover_url=safe_cover,
                        content_body=item["url"],
                        status=1,
                        ip_location=f"自动爬取|{item['source']}"
                    )
                    db.add(new_post)

                    # === 关键修复：逐条提交 ===
                    # 避免一条失败导致整批回滚
                    await db.commit()
                    new_count += 1

                except Exception as e:
                    await db.rollback()
                    logger.error(f"❌ 单条入库失败: {e} | 标题: {item.get('title', '')}")

            logger.info(f"✅ [定时任务] 抓取完成，成功入库: {new_count} 篇")

    except Exception as e:
        logger.error(f"❌ [定时任务] 爬虫运行异常: {e}")


def start_scheduler():
    """
    启动调度器并添加任务
    """
    # 每隔 1 小时抓取一次
    scheduler.add_job(
        scheduled_crawl_task,
        trigger=IntervalTrigger(hours=1),
        id="news_crawler",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
    logger.info("⏰ [系统] 定时任务调度器已启动 (周期:一个小时)")
