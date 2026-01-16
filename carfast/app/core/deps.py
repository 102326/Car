"""
FastAPI 依赖注入函数
提供对全局连接的便捷访问
"""
from fastapi import Request, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from aio_pika import Channel

from app.core.connections import ConnectionManager


def get_connections(request: Request) -> ConnectionManager:
    """
    获取连接管理器
    
    用法:
        @router.get("/")
        async def endpoint(conn: ConnectionManager = Depends(get_connections)):
            mongo_db = conn.get_mongo_db()
            redis = conn.get_redis()
    """
    return request.app.state.connections


def get_mongo_db(request: Request) -> AsyncIOMotorDatabase:
    """
    获取 MongoDB 数据库
    
    用法:
        @router.get("/data")
        async def get_data(mongo_db = Depends(get_mongo_db)):
            data = await mongo_db.my_collection.find().to_list(100)
            return data
    """
    return request.app.state.connections.get_mongo_db()


def get_redis(request: Request) -> Redis:
    """
    获取 Redis 客户端
    
    用法:
        @router.get("/cache")
        async def get_cache(redis: Redis = Depends(get_redis)):
            value = await redis.get("key")
            return {"value": value}
    """
    return request.app.state.connections.get_redis()


def get_rabbitmq_channel(request: Request) -> Channel:
    """
    获取 RabbitMQ 频道
    
    用法:
        @router.post("/publish")
        async def publish(channel: Channel = Depends(get_rabbitmq_channel)):
            await channel.default_exchange.publish(...)
    """
    return request.app.state.connections.get_rabbitmq_channel()
