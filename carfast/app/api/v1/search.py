from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.es_service import CarESService
from app.schemas.search import SearchParams  # 确保 app/schemas/search.py 已创建
from app.utils.jwt import MyJWT
from app.models.user import UserAuth

router = APIRouter()


# ✅ 改为 POST 方法，以支持复杂的 JSON Body 传参
@router.post("/cars", summary="[Pro] 高级搜索接口")
async def search_cars_pro(
        request: Request,
        params: SearchParams,  # 使用 Pydantic 模型接收前端的 JSON
        db: AsyncSession = Depends(get_db)
):
    """
    搜索接口 (支持筛选、排序、聚合)
    - q: 关键词
    - brand: 品牌
    - min_price/max_price: 价格区间
    - sort_by: 排序
    """

    # --- 柔性鉴权 ---
    current_user = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = MyJWT.decode_token(token)
            current_user = await db.get(UserAuth, int(payload.get("sub")))
        except:
            pass

    user_identity = f"会员({current_user.phone})" if current_user else "游客"
    print(f"🔍 [{user_identity}] 高级搜索: {params.dict()}")

    # ✅ 调用 ES 服务的高级搜索方法
    result = await CarESService.search_cars_pro(params)

    return {
        "code": 200,
        "msg": "success",
        "data": result,
        "meta": {
            "identity": user_identity
        }
    }