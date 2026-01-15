# Car-Superman/carfast/app/tasks/sync_tasks.py
import logging
import asyncio
from asgiref.sync import async_to_sync
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# 引入你的项目依赖
from app.core.database import AsyncSessionLocal
from app.services.es_service import CarESService
from app.models.car import CarModel, CarSeries

# 设置专用日志
logger = logging.getLogger("celery.sync")


async def _async_sync_logic(car_id: int, action: str):
    """
    [异步核心] 负责查库和写 ES
    """
    logger.info(f"🔄 [开始] 处理车辆同步 Task: ID={car_id}, Action={action}")

    # 1. 删除逻辑
    if action == "delete":
        await CarESService.delete_car_doc(car_id)
        return f"Car {car_id} deleted"

    # 2. 新增/更新逻辑 (Fetch-on-Write)
    async with AsyncSessionLocal() as session:
        try:
            # 预加载关联表，防止 Lazy Load 报错
            stmt = select(CarModel).options(
                selectinload(CarModel.series).selectinload(CarSeries.brand)
            ).where(CarModel.id == car_id)

            result = await session.execute(stmt)
            car = result.scalars().first()

            if not car:
                logger.warning(f"⚠️ 数据库无此车 (ID={car_id})，执行防御性删除")
                await CarESService.delete_car_doc(car_id)
                return "Car not found, deleted"

            # 3. 展平数据 (Flatten)
            series_name = car.series.name if car.series else ""
            brand_name = car.series.brand.name if (car.series and car.series.brand) else ""

            # 处理 extra_tags
            tags_text = ""
            if car.extra_tags and isinstance(car.extra_tags, dict):
                # 提取所有 value 拼成字符串
                values = []
                for val in car.extra_tags.values():
                    if isinstance(val, list):
                        values.extend([str(v) for v in val])
                    else:
                        values.append(str(val))
                tags_text = " ".join(values)

            doc = {
                "id": car.id,
                "name": car.name,
                "brand_name": brand_name,
                "series_name": series_name,
                "price": float(car.price_guidance) if car.price_guidance else 0.0,
                "year": car.year,
                "status": car.status,
                "tags_text": tags_text,
                "updated_at": car.updated_at.isoformat() if car.updated_at else None
            }

            # 4. 写入 ES
            await CarESService.sync_car_doc(doc)
            logger.info(f"✅ [成功] Car {car_id} 已同步到 ES")
            return f"Car {car_id} synced"

        except Exception as e:
            logger.error(f"❌ [失败] 处理 Car {car_id} 报错: {str(e)}")
            raise e


@shared_task(
    name="sync_car_to_es",  # 显式命名，防止自动命名冲突
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def sync_car_task(self, car_id: int, action: str = "update"):
    """
    [Celery 入口]
    """
    try:
        # 桥接异步代码
        return async_to_sync(_async_sync_logic)(car_id, action)
    except Exception as e:
        logger.error(f"💥 Task 崩溃，准备重试: {e}")
        raise self.retry(exc=e)