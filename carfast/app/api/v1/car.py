from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.car import CarModel, CarSeries, CarBrand
from app.schemas.car import CarDetailResponse

router = APIRouter()

@router.get("/{car_id}", response_model=CarDetailResponse, summary="获取车辆详情")
async def get_car_detail(car_id: int, db: AsyncSession = Depends(get_db)):
    # 1. 联表查询: Model -> Series -> Brand
    stmt = (
        select(CarModel)
        .options(
            joinedload(CarModel.series).joinedload(CarSeries.brand)
        )
        .where(CarModel.id == car_id)
    )
    result = await db.execute(stmt)
    car = result.scalars().first()

    if not car:
        raise HTTPException(status_code=404, detail="车辆不存在")

    # 2. 组装响应数据
    # 注意: 这里我们mock了一些图片数据，让前端不至于一片空白
    return CarDetailResponse(
        id=car.id,
        name=car.name,
        year=car.year,
        price=float(car.price_guidance) if car.price_guidance else 0.0,
        status=car.status,
        brand_name=car.series.brand.name,
        brand_logo=car.series.brand.logo_url,
        series_name=car.series.name,
        series_level=car.series.level,
        energy_type=car.series.energy_type,
        extra_tags=car.extra_tags,
        # 模拟 3 张外观图
        images=[
            "https://via.placeholder.com/800x600/2196F3/FFFFFF?text=Front+View",
            "https://via.placeholder.com/800x600/4CAF50/FFFFFF?text=Side+View",
            "https://via.placeholder.com/800x600/FFC107/FFFFFF?text=Interior"
        ]
    )