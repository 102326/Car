import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from app.services.car_assembler import fetch_and_assemble_car_docs
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
            await CarESService.delete_car_doc(car_id)
        else:
            # ✅ 改用公共组件 (虽然是单条，但也传 List)
            docs = await fetch_and_assemble_car_docs([car_id])
            if docs:
                await CarESService.sync_car_doc(docs[0])
                logger.info(f"✅ Synced Car ID: {car_id}")
            else:
                logger.warning(f"⚠️ Car ID {car_id} not found in DB")

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