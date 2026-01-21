import logging
from typing import List
from elasticsearch.helpers import async_bulk
from app.core.es import es_client

logger = logging.getLogger("es_service")


class CarESService:
    INDEX_NAME = "pylab_cars_v1"

    @classmethod
    async def create_index_if_not_exists(cls):
        """初始化索引结构"""
        client = es_client.get_client()
        if await client.indices.exists(index=cls.INDEX_NAME):
            return

        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "1s"
            },
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "name": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart"
                    },
                    "brand_name": {"type": "keyword"},
                    "series_name": {"type": "keyword"},
                    "series_level": {"type": "keyword"},
                    "energy_type": {"type": "keyword"},
                    "price": {"type": "double"},
                    "year": {"type": "keyword"},
                    "status": {"type": "integer"},
                    "tags_text": {"type": "text", "analyzer": "ik_smart"},
                    "updated_at": {"type": "date"}
                }
            }
        }
        await client.indices.create(index=cls.INDEX_NAME, body=mapping)
        logger.info(f"✅ ES 索引 {cls.INDEX_NAME} 创建成功")

    @classmethod
    async def sync_car_doc(cls, doc: dict):
        await cls.bulk_sync_cars([doc])

    @classmethod
    async def delete_car_doc(cls, car_id: int):
        await cls.bulk_delete_cars([car_id])

    @classmethod
    async def bulk_sync_cars(cls, docs: list) -> List[int]:
        """🚀 批量 Upsert，返回失败 ID"""
        if not docs:
            return []

        client = es_client.get_client()
        actions = [
            {
                "_index": cls.INDEX_NAME,
                "_id": str(d["id"]),
                "_source": d,
                "_op_type": "index"
            }
            for d in docs
        ]
        return await cls._execute_bulk(client, actions)

    @classmethod
    async def bulk_delete_cars(cls, car_ids: list) -> List[int]:
        """🚀 [新增] 批量删除，返回失败 ID"""
        if not car_ids:
            return []

        client = es_client.get_client()
        actions = [
            {
                "_index": cls.INDEX_NAME,
                "_id": str(cid),
                "_op_type": "delete"
            }
            for cid in car_ids
        ]
        # 删除时如果报 404 (not_found)，通常认为是成功的，不需要重试
        # 但 async_bulk 默认会把 404 算作 error，我们需要在 _execute_bulk 里特殊处理吗？
        # elasticsearch.helpers 默认 delete 404 算成功吗？通常不算 error。
        # 我们统一处理。
        return await cls._execute_bulk(client, actions)

    @classmethod
    async def _execute_bulk(cls, client, actions) -> List[int]:
        """统一执行 Bulk 并提取重试 ID"""
        failed_ids = []
        try:
            success_count, errors = await async_bulk(client, actions, raise_on_error=False)

            if errors:
                for err in errors:
                    # 提取 info，可能是 index, delete, create, update
                    op_type = next(iter(err.keys()))
                    info = err[op_type]
                    status = info.get('status')

                    # 忽略 404 删除错误 (本来就没有，删除了也算成功)
                    if op_type == 'delete' and status == 404:
                        continue

                    doc_id = info.get('_id')
                    error_reason = info.get('error')
                    logger.error(f"❌ [ES] {op_type} ID {doc_id} 失败: {error_reason}")
                    if doc_id:
                        failed_ids.append(int(doc_id))

        except Exception as e:
            logger.error(f"💥 [ES] Bulk 请求系统级崩溃: {e}")
            # 系统级崩溃，所有涉及的 ID 都需要重试
            return [int(a['_id']) for a in actions]

        return failed_ids

    @classmethod
    async def search_cars(cls, q: str, page: int = 1, size: int = 10):
        # ... (搜索代码保持不变) ...
        client = es_client.get_client()
        query_body = {
            "from": (page - 1) * size,
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": q,
                                "fields": ["name^3", "brand_name^2", "series_name"],
                                "type": "best_fields"
                            }
                        }
                    ],
                    "filter": [{"term": {"status": 1}}]
                }
            },
            "highlight": {
                "fields": {"name": {}},
                "pre_tags": ["<em class='highlight'>"],
                "post_tags": ["</em>"]
            }
        }
        try:
            resp = await client.search(index=cls.INDEX_NAME, body=query_body)
        except Exception:
            return {"total": 0, "list": [], "page": page, "size": size}

        hits = resp["hits"]["hits"]
        results = []
        for hit in hits:
            source = hit["_source"]
            if "highlight" in hit and "name" in hit["highlight"]:
                source["name_highlight"] = hit["highlight"]["name"][0]
            source["_id"] = hit["_id"]
            results.append(source)

        return {"total": resp["hits"]["total"]["value"], "list": results, "page": page, "size": size}