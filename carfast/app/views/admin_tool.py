from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.services.news_crawler import AutoNewsCrawler
from app.models.Content_Resource import CMSPost, PostType
from app.core.database import get_db, AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserAuth

admin_router = APIRouter(prefix="/admin/tools", tags=["管理员工具箱"])


async def run_crawler_task():
    print("🚀 [后台任务] 开始执行全量抓取...")
    crawler = AutoNewsCrawler()
    try:
        # 1. 爬取
        crawl_result = await crawler.run_all()
        all_articles = crawl_result["all_flat"]

        if not all_articles:
            print("⚠️ [后台任务] 未抓取到数据 (可能是被反爬拦截)")
            return

        # 2. 入库
        async with AsyncSessionLocal() as db:
            
            # --- 用户自动修正逻辑 (修复版) ---
            # 优先尝试获取 ID=1 的用户
            admin_user = await db.get(UserAuth, 1)
            
            if not admin_user:
                print("⚠️ [后台任务] 管理员(ID=1)不存在，尝试创建...")
                try:
                    admin_user = UserAuth(
                        id=1,
                        phone="13800000000",
                        status=1,
                    )
                    db.add(admin_user)
                    await db.flush() # 尝试提交
                    print("✅ [后台任务] 管理员用户创建成功")
                except Exception as e:
                    # 如果创建失败（比如ID冲突），回滚事务并尝试获取任意一个现有用户
                    await db.rollback()
                    print(f"⚠️ [后台任务] 创建失败({e})，尝试使用现有用户...")
                    
                    # 再次尝试获取 ID=1 (可能并发创建了)
                    admin_user = await db.get(UserAuth, 1)
                    
                    # 如果还是没有，获取表里第一个用户
                    if not admin_user:
                        stmt = select(UserAuth).limit(1)
                        res = await db.execute(stmt)
                        admin_user = res.scalars().first()
            
            if not admin_user:
                print("❌ [后台任务] 严重错误：数据库无任何用户，无法归档文章！请先注册一个用户。")
                return

            print(f"👤 [后台任务] 使用归档用户 ID={admin_user.id}")
            # -------------------------------

            admin_user_id = admin_user.id
            new_count = 0

            for item in all_articles:
                try:
                    # 去重检查 (URL)
                    stmt = select(CMSPost).where(CMSPost.content_body == item["url"])
                    result = await db.execute(stmt)
                    if result.scalars().first():
                        continue

                    # === 修复点 1: 字段安全截断 ===
                    # 数据库 title 定义是 String(100)，cover_url 是 String(255)
                    # 超过长度会导致整个事务提交失败
                    safe_title = item["title"][:99] if item["title"] else "无标题"
                    safe_cover = item["cover"][:254] if item["cover"] else ""

                    # 入库
                    new_post = CMSPost(
                        user_id=admin_user_id,
                        title=safe_title,
                        post_type=PostType.ARTICLE,
                        cover_url=safe_cover,
                        content_body=item["url"], # 这里存URL
                        status=1,
                        ip_location=f"自动抓取|{item['source']}"
                    )
                    db.add(new_post)
                    
                    # === 修复点 2: 逐条提交 ===
                    # 这样即使某一条报错，也不会影响其他正常数据的入库
                    await db.commit()
                    
                    new_count += 1
                except Exception as e:
                    await db.rollback() # 出错回滚当前条目
                    print(f"⚠️ 单条入库失败: {e} | 标题: {item.get('title', '')}")

            # 循环结束不需要再大 commit，因为已经逐条提交了
            print(f"✅ [后台任务] 全量抓取完成，成功入库: {new_count} 篇")

    except Exception as e:
        print(f"❌ [后台任务] 全局异常: {e}")


@admin_router.post("/sync-news", summary="手动触发全网资讯抓取 (后台运行)")
async def sync_external_news(background_tasks: BackgroundTasks):
    """
    触发后台爬虫任务。
    接口会立即返回，爬虫将在后台运行。
    """
    background_tasks.add_task(run_crawler_task)
    return {"message": "爬虫任务已启动，正在后台拼命抓取中... 请查看控制台日志"}
