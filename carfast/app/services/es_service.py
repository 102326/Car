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

    @classmethod
    async def search_cars(cls, q: str, page: int = 1, size: int = 10):
        client = es_client.get_client()

        # 1. 构建 DSL
        query_body = {
            "from": (page - 1) * size,
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": q,
                                # 你的 Mapping 里 brand_name 是 keyword，name 是 text
                                # 这里的权重设置依然有效
                                "fields": ["name^3", "brand_name^2", "series_name"],
                                # fuzziness 对 keyword 字段无效，主要针对 name 字段生效
                                "type": "best_fields"
                            }
                        }
                    ],
                    "filter": [
                        # 只搜状态正常的车 (你定义的 mapping 里有 status 字段)
                        {"term": {"status": 1}}
                    ]
                }
            },
            "highlight": {
                "fields": {
                    "name": {}
                    # keyword 类型的 brand_name 通常不支持普通的高亮，这里先只高亮 name
                },
                "pre_tags": ["<em class='highlight'>"],
                "post_tags": ["</em>"]
            }
        }

        try:
            resp = await client.search(index=cls.INDEX_NAME, body=query_body)
        except Exception as e:
            logger.error(f"⚠️ ES 搜索异常: {e}")
            # 返回空结果结构，防止前端报错
            return {"total": 0, "list": [], "page": page, "size": size}

        # 2. 数据清洗
        hits = resp["hits"]["hits"]
        results = []
        for hit in hits:
            source = hit["_source"]
            # 处理高亮
            if "highlight" in hit:
                if "name" in hit["highlight"]:
                    source["name_highlight"] = hit["highlight"]["name"][0]

            source["_id"] = hit["_id"]
            results.append(source)

        return {
            "total": resp["hits"]["total"]["value"],
            "list": results,
            "page": page,
            "size": size
        }