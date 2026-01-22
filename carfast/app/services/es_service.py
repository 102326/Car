# carfast/app/services/es_service.py
import logging
from app.core.es import es_client

logger = logging.getLogger("es_service")


class CarESService:
    # 索引名称
    INDEX_NAME = "pylab_cars_v1"

    @classmethod
    async def create_index_if_not_exists(cls):
        """
        初始化索引结构 (Mapping)
        注意：需要安装 ik 分词插件 (elasticsearch-plugin install analysis-ik)
        如果未安装，请将 analyzer 改为 "standard"
        """
        client = es_client.get_client()
        if await client.indices.exists(index=cls.INDEX_NAME):
            return

        # 定义 Mapping：根据 CarModel 字段定制
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "1s"  # 1秒刷新一次，平衡实时性与性能
            },
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    # 核心搜索字段
                    "name": {
                        "type": "text",
                        "analyzer": "ik_max_word",  # 最大细粒度分词
                        "search_analyzer": "ik_smart"
                    },
                    # 筛选字段 (Keyword 用于精确匹配/聚合)
                    "brand_name": {"type": "keyword"},
                    "series_name": {"type": "keyword"},
                    "series_level": {"type": "keyword"},  # 紧凑型/SUV等
                    "energy_type": {"type": "keyword"},  # 燃油/纯电
                    # 排序/范围筛选字段
                    "price": {"type": "double"},  # 对应 price_guidance
                    "year": {"type": "keyword"},
                    "status": {"type": "integer"},
                    # 标签全文检索
                    "tags_text": {"type": "text", "analyzer": "ik_smart"},
                    # 时间用于兜底校验
                    "updated_at": {"type": "date"}
                }
            }
        }

        await client.indices.create(index=cls.INDEX_NAME, body=mapping)
        logger.info(f"✅ ES 索引 {cls.INDEX_NAME} 创建成功")

    @classmethod
    async def sync_car_doc(cls, doc: dict):
        """写入/更新文档"""
        client = es_client.get_client()
        try:
            await client.index(
                index=cls.INDEX_NAME,
                id=str(doc["id"]),
                document=doc
            )
            logger.info(f"📥 [ES] Car {doc['id']} 同步成功")
        except Exception as e:
            logger.error(f"❌ [ES] Car {doc.get('id')} 同步失败: {e}")
            raise e

    @classmethod
    async def delete_car_doc(cls, car_id: int):
        """删除文档"""
        client = es_client.get_client()
        try:
            await client.delete(index=cls.INDEX_NAME, id=str(car_id))
            logger.info(f"🗑️ [ES] Car {car_id} 删除成功")
        except Exception:
            pass  # 忽略 404