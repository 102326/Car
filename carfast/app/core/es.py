# carfast/app/core/es.py
import logging
from elasticsearch import AsyncElasticsearch
from app.config import settings

logger = logging.getLogger(__name__)

class ESClient:
    _client: AsyncElasticsearch = None

    @classmethod
    def get_client(cls) -> AsyncElasticsearch:
        """
        获取 ES 客户端单例 (Lazy Loading)
        """
        if cls._client is None:
            logger.info(f"🔌 初始化 Elasticsearch 连接: {settings.ES_URL}")
            cls._client = AsyncElasticsearch(
                hosts=[settings.ES_URL],
                # 如果你的 ES 设置了密码（生产环境建议设置）：
                # basic_auth=("elastic", "你的密码"),
                verify_certs=False
            )
        return cls._client

    @classmethod
    async def close(cls):
        """关闭连接 (通常在 shutdown event 中调用)"""
        if cls._client:
            await cls._client.close()
            cls._client = None
            logger.info("🔌 Elasticsearch 连接已关闭")

# 导出单例对象
es_client = ESClient