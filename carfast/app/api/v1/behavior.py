import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from redis.asyncio import Redis

from app.core.database import get_db
from app.core.redis import get_redis
from app.utils.deps import get_current_user
from app.models.user import UserAuth
from app.models.car import CarModel
from app.schemas.car import CarDetailResponse

router = APIRouter()


# -------------------------
# 🕒 浏览历史 (Redis ZSet)
# -------------------------
@router.post("/history/{car_id}", summary="记录浏览历史")
async def add_history(
        car_id: int,
        user: UserAuth = Depends(get_current_user),
        redis: Redis = Depends(get_redis)
):
    key = f"history:user:{user.id}"
    timestamp = int(time.time())

    # ZADD: 更新/添加浏览时间
    await redis.zadd(key, {str(car_id): timestamp})

    # 保持最近 50 条记录
    count = await redis.zcard(key)
    if count > 50:
        await redis.zremrangebyrank(key, 0, count - 51)

    return {"msg": "ok"}


@router.get("/history", response_model=list[CarDetailResponse], summary="获取浏览足迹")
async def get_history(
        user: UserAuth = Depends(get_current_user),
        redis: Redis = Depends(get_redis),
        db: AsyncSession = Depends(get_db)
):
    key = f"history:user:{user.id}"
    # ZREVRANGE: 按时间倒序获取最近 20 条
    car_ids = await redis.zrevrange(key, 0, 19)

    if not car_ids:
        return []

    ids = [int(i) for i in car_ids]

    # 查库获取详情
    stmt = select(CarModel).where(CarModel.id.in_(ids))
    result = await db.execute(stmt)
    cars = result.scalars().all()

    # 内存排序 (Redis 顺序 -> SQL 结果顺序)
    cars_map = {c.id: c for c in cars}
    sorted_cars = [cars_map[cid] for cid in ids if cid in cars_map]

    return sorted_cars


# -------------------------
# ❤️ 收藏列表 (PostgreSQL)
# -------------------------
@router.post("/favorite/{car_id}", summary="收藏/取消收藏")
async def toggle_favorite(
        car_id: int,
        user: UserAuth = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    # ✅ Schema Rule: 使用 car.user_favorite_cars
    check_sql = text("SELECT 1 FROM car.user_favorite_cars WHERE user_id=:uid AND car_id=:cid")
    result = await db.execute(check_sql, {"uid": user.id, "cid": car_id})
    exists = result.first()

    if exists:
        del_sql = text("DELETE FROM car.user_favorite_cars WHERE user_id=:uid AND car_id=:cid")
        await db.execute(del_sql, {"uid": user.id, "cid": car_id})
        is_fav = False
    else:
        ins_sql = text("INSERT INTO car.user_favorite_cars (user_id, car_id) VALUES (:uid, :cid)")
        await db.execute(ins_sql, {"uid": user.id, "cid": car_id})
        is_fav = True

    await db.commit()
    return {"is_favorite": is_fav}


@router.get("/favorite/check/{car_id}", summary="检查收藏状态")
async def check_favorite(
        car_id: int,
        user: UserAuth = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    sql = text("SELECT 1 FROM car.user_favorite_cars WHERE user_id=:uid AND car_id=:cid")
    result = await db.execute(sql, {"uid": user.id, "cid": car_id})
    return {"is_favorite": bool(result.first())}


@router.get("/favorite", response_model=list[CarDetailResponse], summary="获取收藏列表")
async def get_favorites(
        user: UserAuth = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取用户的收藏列表
    采用两步查询策略，确保 schema 安全并兼容 ORM
    """
    # 1. 第一步：使用原生 SQL 查出收藏的 car_id 列表
    # 这样可以精确指定 car. schema，避开 SQLAlchemy TextClause Join 的坑
    sql = text("SELECT car_id FROM car.user_favorite_cars WHERE user_id = :uid ORDER BY created_at DESC")
    result = await db.execute(sql, {"uid": user.id})
    fav_car_ids = result.scalars().all()

    if not fav_car_ids:
        return []

    # 2. 第二步：使用标准 ORM 根据 ID 列表查询车辆详情
    stmt = select(CarModel).where(CarModel.id.in_(fav_car_ids))
    car_result = await db.execute(stmt)
    cars = car_result.scalars().all()

    # 3. (可选) 内存排序：保持收藏的时间顺序
    # 构建 ID -> Car 映射
    cars_map = {car.id: car for car in cars}
    # 按 fav_car_ids 的顺序重组列表
    sorted_cars = [cars_map[cid] for cid in fav_car_ids if cid in cars_map]

    return sorted_cars