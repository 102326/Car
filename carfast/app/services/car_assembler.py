# carfast/app/services/car_assembler.py
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.core.database import AsyncSessionLocal
from app.models.car import CarModel, CarSeries


async def fetch_and_assemble_car_docs(car_ids: List[int]) -> List[dict]:
    """
    【公共组件】批量查库并组装 ES 文档
    支持传入单个 ID (list len=1) 或 批量 ID
    """
    if not car_ids:
        return []

    docs = []
    async with AsyncSessionLocal() as session:
        # 1. 批量查询 (解决 N+1 问题)
        stmt = (
            select(CarModel)
            .options(joinedload(CarModel.series).joinedload(CarSeries.brand))
            .where(CarModel.id.in_(car_ids))  # 关键：使用 IN 查询
        )
        result = await session.execute(stmt)
        cars = result.scalars().all()

        # 2. 内存组装
        for car in cars:
            # 处理 extra_tags (逻辑复用)
            tags_text = ""
            if car.extra_tags:
                if isinstance(car.extra_tags, dict):
                    tags_text = " ".join(str(v) for v in car.extra_tags.values())
                elif isinstance(car.extra_tags, list):
                    tags_text = " ".join(str(v) for v in car.extra_tags)
                else:
                    tags_text = str(car.extra_tags)

            doc = {
                "id": car.id,
                "name": car.name,
                "price": float(car.price_guidance) if car.price_guidance else 0.0,
                "year": car.year,
                "status": car.status,
                "tags_text": tags_text,
                "updated_at": car.updated_at.isoformat() if car.updated_at else None,
                # 宽表字段
                "series_name": car.series.name if car.series else "",
                "series_level": car.series.level if car.series else "",
                "brand_name": car.series.brand.name if (car.series and car.series.brand) else "",
                "energy_type": car.series.energy_type if car.series else ""
            }
            docs.append(doc)

    return docs