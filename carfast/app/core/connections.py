"""
统一的数据库和工具连接管理器
在 FastAPI lifespan 中初始化，通过 app.state 访问
"""
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from pymilvus import connections
from aio_pika import connect_robust, Connection as RabbitMQConnection

from app.config import settings

logger = logging.getLogger("uvicorn")


class ConnectionManager:
    """连接管理器 - 管理所有全局连接"""
    
    def __init__(self):
        # MongoDB
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.mongo_db = None
        
        # Redis
        self.redis_client: Optional[Redis] = None
        
        # RabbitMQ
        self.rabbitmq_connection: Optional[RabbitMQConnection] = None
        self.rabbitmq_channel = None
        
        # Milvus
        self.milvus_connected: bool = False
    
    async def connect_all(self):
        """连接所有服务"""
        logger.info("开始初始化所有连接...")
        
        # 1. MongoDB
        await self._connect_mongodb()
        
        # 2. Redis
        await self._connect_redis()
        
        # 3. RabbitMQ
        await self._connect_rabbitmq()
        
        # 4. Milvus
        await self._connect_milvus()
        
        logger.info("所有连接初始化完成")
    
    async def disconnect_all(self):
        """断开所有连接"""
        logger.info("开始断开所有连接...")
        
        # 断开 MongoDB
        if self.mongo_client is not None:
            self.mongo_client.close()
            logger.info("MongoDB 连接已关闭")
        
        # 断开 Redis
        if self.redis_client is not None:
            await self.redis_client.aclose()
            logger.info("Redis 连接已关闭")
        
        # 断开 RabbitMQ
        if self.rabbitmq_connection is not None and not self.rabbitmq_connection.is_closed:
            await self.rabbitmq_connection.close()
            logger.info("RabbitMQ 连接已关闭")
        
        # 断开 Milvus
        if self.milvus_connected:
            try:
                connections.disconnect("default")
                logger.info("Milvus 连接已关闭")
            except:
                pass
        
        logger.info("所有连接已断开")
    
    # ==========================================
    # MongoDB 连接
    # ==========================================
    async def _connect_mongodb(self):
        """连接 MongoDB"""
        try:
            logger.info(f"正在连接 MongoDB: {settings.MONGO_URL.split('@')[-1]}")
            self.mongo_client = AsyncIOMotorClient(
                settings.MONGO_URL,
                serverSelectionTimeoutMS=5000
            )
            
            # 测试连接
            await self.mongo_client.admin.command('ping')
            
            # 获取数据库
            self.mongo_db = self.mongo_client[settings.MONGO_DB_NAME]
            
            logger.info(f"✅ MongoDB 连接成功: {settings.MONGO_DB_NAME}")
            
        except Exception as e:
            logger.error(f"❌ MongoDB 连接失败: {e}")
            self.mongo_client = None
            self.mongo_db = None
    
    # ==========================================
    # Redis 连接
    # ==========================================
    async def _connect_redis(self):
        """连接 Redis"""
        try:
            logger.info(f"正在连接 Redis: {settings.REDIS_URL}")
            self.redis_client = Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # 测试连接
            await self.redis_client.ping()
            
            logger.info("✅ Redis 连接成功")
            
        except Exception as e:
            logger.error(f"❌ Redis 连接失败: {e}")
            self.redis_client = None
    
    # ==========================================
    # RabbitMQ 连接
    # ==========================================
    async def _connect_rabbitmq(self):
        """连接 RabbitMQ"""
        try:
            logger.info(f"正在连接 RabbitMQ...")
            self.rabbitmq_connection = await connect_robust(settings.RABBITMQ_URL)
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()
            
            logger.info("✅ RabbitMQ 连接成功")
            
        except Exception as e:
            logger.warning(f"⚠️ RabbitMQ 连接失败（非关键服务）: {e}")
            self.rabbitmq_connection = None
            self.rabbitmq_channel = None
    
    # ==========================================
    # Milvus 连接
    # ==========================================
    async def _connect_milvus(self):
        """连接 Milvus"""
        try:
            logger.info(f"正在连接 Milvus: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            
            self.milvus_connected = True
            logger.info("✅ Milvus 连接成功")
            
        except Exception as e:
            logger.warning(f"⚠️ Milvus 连接失败（非关键服务）: {e}")
            self.milvus_connected = False
    
    # ==========================================
    # 便捷访问方法
    # ==========================================
    def get_mongo_db(self):
        """获取 MongoDB 数据库"""
        if self.mongo_db is None:
            raise RuntimeError("MongoDB 未连接")
        return self.mongo_db
    
    def get_redis(self):
        """获取 Redis 客户端"""
        if self.redis_client is None:
            raise RuntimeError("Redis 未连接")
        return self.redis_client
    
    def get_rabbitmq_channel(self):
        """获取 RabbitMQ 频道"""
        if self.rabbitmq_channel is None:
            raise RuntimeError("RabbitMQ 未连接")
        return self.rabbitmq_channel
    
    def is_milvus_connected(self):
        """检查 Milvus 是否连接"""
        return self.milvus_connected


# 全局单例
connection_manager = ConnectionManager()
