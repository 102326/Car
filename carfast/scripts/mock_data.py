import asyncio
import sys
import os
import random
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from elasticsearch import AsyncElasticsearch, helpers

# 目标数据量 (5万条足以把3个节点跑热)
TARGET_COUNT = 800000
BATCH_SIZE = 2000

# 基础词库
BRANDS = ["宝马", "奔驰", "奥迪", "特斯拉", "比亚迪", "丰田", "本田", "理想", "蔚来", "小米"]
LEVELS = ["紧凑型SUV", "中型SUV", "大型SUV", "紧凑型车", "中型车", "跑车"]
ENERGIES = ["汽油", "纯电", "插电混动", "增程"]
YEARS = ["2022", "2023", "2024", "2025"]


async def generate_mock_data():
    es = AsyncElasticsearch(settings.ES_URL)
    index_name = "pylab_cars_v1"

    print(f"🔥 准备向 {index_name} 灌入 {TARGET_COUNT} 条全字段数据...")

    actions = []
    total_inserted = 0

    for i in range(TARGET_COUNT):
        # 随机生成属性
        brand = random.choice(BRANDS)
        level = random.choice(LEVELS)
        energy = random.choice(ENERGIES)
        year = random.choice(YEARS)
        series = f"{brand} {random.choice(['X', 'E', 'Pro', 'Max', 'Ultra'])}{random.randint(3, 9)}"

        # 构造文档
        doc = {
            "_index": index_name,
            "_source": {
                "id": 10000 + i,
                "name": f"{year}款 {brand} {series} {energy}版",  # 对应 name
                "brand_name": brand,  # 对应 keyword
                "series_name": series,
                "series_level": level,
                "energy_type": energy,
                "price": round(random.uniform(10.0, 100.0), 2),  # 随机价格 10万-100万
                "year": year,
                "status": 1,  # ✅ 必须是1，否则会被你的代码 filter 掉
                "tags_text": f"特价 {level} {energy} 自动驾驶",
                "updated_at": datetime.now().isoformat()
            }
        }
        actions.append(doc)

        if len(actions) >= BATCH_SIZE:
            await helpers.async_bulk(es, actions)
            total_inserted += len(actions)
            print(f"🚀 已装填: {total_inserted}/{TARGET_COUNT}")
            actions = []

    if actions:
        await helpers.async_bulk(es, actions)

    print(f"✅ 任务完成！共计 {TARGET_COUNT} 条有效数据。")
    print("👉 请重启 FastAPI 后端，然后开始 JMeter 压测！")
    await es.close()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(generate_mock_data())