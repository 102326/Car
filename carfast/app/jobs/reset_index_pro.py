import asyncio
import sys
import os

# 加入路径以便导入配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from elasticsearch import AsyncElasticsearch

# 🔥 集群版配置
INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 3,  # ✅ 强制 3 分片 (激活 es01, es02, es03)
        "number_of_replicas": 0,  # 压测不想要副本，追求极致写入
        "refresh_interval": "1s"
    },
    "mappings": {
        # 👇这里完全照搬您的 CarESService 定义
        "properties": {
            "id": {"type": "integer"},
            "name": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart"
            },
            "brand_name": {"type": "keyword"},  # ✅ 聚合/排序专用
            "series_name": {"type": "keyword"},
            "series_level": {"type": "keyword"},  # 级别 (中型SUV等)
            "energy_type": {"type": "keyword"},  # 能源 (汽油/纯电)
            "price": {"type": "double"},  # 价格
            "year": {"type": "keyword"},
            "status": {"type": "integer"},  # 上架状态
            "tags_text": {"type": "text", "analyzer": "ik_smart"},
            "updated_at": {"type": "date"}
        }
    }
}


async def reset_index():
    es = AsyncElasticsearch(settings.ES_URL)
    index_name = "pylab_cars_v1"  # 强制写死，防止配置读取错误

    print(f"🔥 [集群模式] 连接 ES: {settings.ES_URL}")

    # 1. 删
    if await es.indices.exists(index=index_name):
        print(f"🗑️ 删除旧索引: {index_name}")
        await es.indices.delete(index=index_name)

    # 2. 建
    print(f"🛠️ 创建新索引 (Shards: 3, Mapping: Sync with Prod)...")
    await es.indices.create(index=index_name, body=INDEX_SETTINGS)

    print("✅ 索引结构同步完成！已适配集群分片。")
    await es.close()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_index())