"""
Alembic 环境配置文件
用于自动生成和执行数据库迁移脚本
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 导入配置和模型
from app.config import settings
from app.models import Base  # 导入 Base，包含所有模型元数据

# Alembic Config 对象
config = context.config

# 从 .env 设置数据库 URL
config.set_main_option("sqlalchemy.url", settings.DB_URL)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置目标元数据（包含所有模型的表结构）
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式：生成 SQL 脚本但不执行
    
    用法:
        alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # PostgreSQL 模式设置
        version_table_schema=target_metadata.schema,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """执行迁移的核心函数"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # 设置 PostgreSQL 模式
        version_table_schema=target_metadata.schema,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步执行迁移（用于异步数据库驱动如 asyncpg）"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    在线模式：连接数据库并执行迁移
    
    用法:
        alembic upgrade head
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
