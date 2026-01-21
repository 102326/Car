import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select
from sqlalchemy.orm import joinedload

# --- 核心架构组件引入 ---
# 1. 引入数据库会话
from app.core.database import AsyncSessionLocal
# 2. 引入模型
from app.models.car import CarModel, CarSeries, CarBrand
# 3. 【关键】引入封装好的 ES 服务，复用连接和写入逻辑
from app.services.es_service import CarESService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CDC_Sync")


async def fetch_full_car_data(car_id: int):
    """
    【写时反查核心逻辑】
    利用 ORM 的 joinedload 一次性把 品牌、车系、车型 全查出来
    构建宽表数据
    """
    async with AsyncSessionLocal() as session:
        # 你的数据在 car 模式，有了 database.py 的配置，这里就能查到了
        stmt = (
            select(CarModel)
            .options(
                joinedload(CarModel.series).joinedload(CarSeries.brand)
            )
            .where(CarModel.id == car_id)
        )
        result = await session.execute(stmt)
        car = result.scalar_one_or_none()

        if not car:
            return None

        # === 🛡️ 核心修复：更健壮的 tags 处理 ===
        # 无论 extra_tags 存的是 1 (int), "abc" (str), 还是 {"tag": "x"} (dict)
        # 都能安全转成字符串，不会报错
        tags_text = ""
        if car.extra_tags:
            if isinstance(car.extra_tags, dict):
                tags_text = " ".join(str(v) for v in car.extra_tags.values())
            elif isinstance(car.extra_tags, list):
                tags_text = " ".join(str(v) for v in car.extra_tags)
            else:
                tags_text = str(car.extra_tags)
        # ======================================

        return {
            "id": car.id,
            "name": car.name,
            "price": float(car.price_guidance) if car.price_guidance else 0.0,
            "year": car.year,
            "status": car.status,
            "tags_text": tags_text,

            # 宽表字段
            "series_name": car.series.name if car.series else "",
            "series_level": car.series.level if car.series else "",
            "brand_name": car.series.brand.name if (car.series and car.series.brand) else "",
            "energy_type": car.series.energy_type if car.series else ""
        }


async def process_message(msg):
    """处理 Debezium 的 CDC 消息"""
    try:
        if not msg.value:
            return

        payload = json.loads(msg.value)['payload']
        op = payload['op']

        # 获取 ID
        row_data = payload.get('after') or payload.get('before')
        if not row_data:
            return

        car_id = row_data['id']

        if op == 'd':
            # === 删除操作 ===
            # 调用 Service 层的方法，不再直接操作 ES
            await CarESService.delete_car_doc(car_id)
            logger.info(f"🗑️ Deleted Car ID: {car_id}")
        else:
            # === 新增/更新操作 ===
            # 1. 反查数据库获取完整数据
            doc = await fetch_full_car_data(car_id)
            if doc:
                # 2. 【关键】调用 Service 层的同步方法
                # 这会自动复用项目配置的 ES 连接
                await CarESService.sync_car_doc(doc)
                logger.info(f"✅ Synced Car ID: {car_id} -> {doc['name']}")
            else:
                logger.warning(f"⚠️ Car ID {car_id} not found in DB, skipping.")

    except Exception as e:
        logger.error(f"❌ Error processing message: {e}", exc_info=True)


async def consume():
    # 启动前先确保索引存在 (防止自动创建导致的 mapping 错误)
    await CarESService.create_index_if_not_exists()
    logger.info("✅ Index checked/created.")

    consumer = AIOKafkaConsumer(
        'cdc.car.car_model',
        bootstrap_servers='localhost:9092',
        group_id='es_sync_group'
    )
    await consumer.start()
    logger.info("🚀 CDC Consumer Started...")
    try:
        async for msg in consumer:
            await process_message(msg)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    # 使用 -m 运行以识别包路径: python -m app.consumers.cdc_sync
    asyncio.run(consume())