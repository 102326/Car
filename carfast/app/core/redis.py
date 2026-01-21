# app/core/redis.py
import redis.asyncio as redis
from app.config import settings

# ✅ 修正：直接复用 settings 中的配置，不硬编码 localhost
pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5
)

async def get_redis():
    client = redis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.close()