"""
数据库连接和会话管理 (SQLAlchemy 2.0)
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool
from app.config import settings

# ==========================================
# 创建异步引擎
# ==========================================
engine = create_async_engine(
    settings.DB_URL,
    echo=True,  # 开发环境可设为 True 查看 SQL
    future=True,
    pool_pre_ping=True,  # 自动检测断开的连接
    poolclass=NullPool,  # 或使用默认连接池
    connect_args={
        "server_settings": {
            # PostgreSQL 模式搜索路径
            "search_path": "car"
        }
    }
)

# ==========================================
# 创建会话工厂
# ==========================================
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后对象仍可访问
    autoflush=False,  # 手动控制 flush
    autocommit=False
)


# ==========================================
# 依赖注入函数：获取数据库会话
# ==========================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入：提供数据库会话
    
    用法:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==========================================
# 初始化数据库表
# ==========================================
async def init_db():
    """
    创建所有表（仅开发环境使用，生产环境用 Alembic 迁移）
    """
    from app.models.user import Base
    
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("✅ 数据库表创建完成")


# ==========================================
# 关闭数据库连接
# ==========================================
async def close_db():
    """
    关闭数据库引擎（应用关闭时调用）
    """
    await engine.dispose()
    print("✅ 数据库连接已关闭")
