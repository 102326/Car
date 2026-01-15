# app/consumers/car_consumer.py
import json
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.car import CarModel, CarSeries, CarBrand
from app.services.es_service import CarESService

logger = logging.getLogger("consumer")


async def process_car_sync(message: dict):
    """
    消费函数：接收 MQ 消息 -> 查 DB -> 写 ES
    Message 格式: {"action": "update", "id": 1001}
    """
    action = message.get("action")
    car_id = message.get("id")

    if not car_id:
        return

    # === 场景 1: 删除 ===
    if action == "delete":
        await CarESService.delete_car(car_id)
        return

    # === 场景 2: 新增/更新 (全量也是走这个逻辑) ===
    # 必须手动创建 Session，因为这是在后台 Worker 进程，不是 Web 请求
    async with AsyncSessionLocal() as session:
        # 预加载 series 和 brand，避免 N+1
        stmt = select(CarModel).options(
            selectinload(CarModel.series).selectinload(CarSeries.brand)
        ).where(CarModel.id == car_id)

        result = await session.execute(stmt)
        car = result.scalars().first()

        if not car:
            logger.warning(f"⚠️ Car ID {car_id} not found in DB, skipping sync.")
            # 也可以选择在这里调用 delete_car，防止脏数据
            await CarESService.delete_car(car_id)
            return

        # 组装 ES 文档数据
        # 注意：这里处理了空值保护
        brand_name = car.series.brand.name if (car.series and car.series.brand) else "未知"
        series_name = car.series.name if car.series else "未知"
        tags_str = " ".join(car.extra_tags.values()) if car.extra_tags else ""

        doc = {
            "id": car.id,
            "name": car.name,
            "brand": brand_name,
            "series": series_name,
            "price": float(car.price_guidance) if car.price_guidance else 0.0,
            "status": car.status,
            "tags": tags_str
        }

        # 写入 ES
        await CarESService.sync_car_to_es(doc)