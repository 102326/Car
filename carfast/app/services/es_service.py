import logging
from typing import List
from elasticsearch.helpers import async_bulk
from app.core.es import es_client
from app.schemas.search import SearchParams

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
    async def search_cars_pro(cls, params: SearchParams):
        """
        🚀 [Pro] 电商级搜索实现
        支持: 关键词 + 多维筛选 + 排序 + 聚合统计
        """
        client = es_client.get_client()

        # 1. 构建 Bool Query
        must_conditions = []
        filter_conditions = [{"term": {"status": 1}}]  # 只看上架的

        # A. 关键词搜索
        if params.q:
            must_conditions.append({
                "multi_match": {
                    "query": params.q,
                    "fields": ["name^3", "brand_name^2", "series_name", "tags_text"],
                    "type": "best_fields",
                    "operator": "and" if len(params.q) < 5 else "or"  # 智能切换精度
                }
            })
        else:
            must_conditions.append({"match_all": {}})

        # B. 结构化筛选 (Filter Context - 不计算分值，快)
        if params.brand:
            filter_conditions.append({"term": {"brand_name": params.brand}})
        if params.series_level:
            filter_conditions.append({"term": {"series_level": params.series_level}})
        if params.energy_type:
            filter_conditions.append({"term": {"energy_type": params.energy_type}})

        # C. 价格范围
        if params.min_price is not None or params.max_price is not None:
            range_query = {}
            if params.min_price is not None: range_query["gte"] = params.min_price
            if params.max_price is not None: range_query["lte"] = params.max_price
            filter_conditions.append({"range": {"price": range_query}})

        # 2. 构建排序 (Sort)
        sort_config = []
        if params.sort_by == "price_asc":
            sort_config = [{"price": "asc"}]
        elif params.sort_by == "price_desc":
            sort_config = [{"price": "desc"}]
        elif params.sort_by == "new":
            sort_config = [{"updated_at": "desc"}]
        else:
            # 默认综合排序: 有关键词按相关度(_score)，无关键词按热度/时间
            if params.q:
                sort_config = ["_score"]
            else:
                sort_config = [{"id": "desc"}]  # 或者按 hot_rank

        # 3. 构建请求体
        body = {
            "from": (params.page - 1) * params.size,
            "size": params.size,
            "query": {
                "bool": {
                    "must": must_conditions,
                    "filter": filter_conditions
                }
            },
            "sort": sort_config,
            # ✨ 聚合统计 (侧边栏筛选器的数据源)
            "aggs": {
                "brands": {"terms": {"field": "brand_name", "size": 20}},
                "levels": {"terms": {"field": "series_level", "size": 10}},
                "energies": {"terms": {"field": "energy_type", "size": 5}}
            },
            "highlight": {
                "fields": {"name": {}},
                "pre_tags": ["<em class='text-red-500 not-italic'>"],  # 适配 Tailwind CSS
                "post_tags": ["</em>"]
            }
        }

        # 4. 执行搜索
        try:
            resp = await client.search(index=cls.INDEX_NAME, body=body)
        except Exception as e:
            logger.error(f"⚠️ ES Search Error: {e}")
            return {"total": 0, "list": [], "facets": {}}

        # 5. 结果清洗
        hits = resp["hits"]["hits"]
        items = []
        for hit in hits:
            source = hit["_source"]
            if "highlight" in hit and "name" in hit["highlight"]:
                source["name_highlight"] = hit["highlight"]["name"][0]
            else:
                source["name_highlight"] = source["name"]

            # 转换价格为 float
            source["price"] = float(source["price"]) if source.get("price") else 0.0
            items.append(source)

        # 6. 提取聚合结果 (Facets)
        aggs = resp.get("aggregations", {})
        facets = {
            "brands": [b["key"] for b in aggs.get("brands", {}).get("buckets", [])],
            "levels": [l["key"] for l in aggs.get("levels", {}).get("buckets", [])],
            "energies": [e["key"] for e in aggs.get("energies", {}).get("buckets", [])]
        }

        return {
            "total": resp["hits"]["total"]["value"],
            "page": params.page,
            "size": params.size,
            "list": items,
            "facets": facets  # 前端用这个生成侧边栏
        }