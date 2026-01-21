from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.es_service import CarESService
from app.schemas.search import SearchParams  # 导入入参模型
from app.utils.jwt import MyJWT
from app.models.user import UserAuth

router = APIRouter()


@router.post("/cars", summary="[Pro] 高级搜索接口")
async def search_cars_pro(
        request: Request,
        params: SearchParams,  # 使用 Post Body 传参，比 Query String 更清晰
        db: AsyncSession = Depends(get_db)
):
    """
    搜索接口 (支持筛选、排序、聚合)

    - **q**: 关键词 (可选)
    - **brand**: 品牌筛选
    - **price**: 价格区间
    - **sort_by**: 排序方式 (price_asc, price_desc, new)
    """

    # --- 鉴权逻辑 (仅用于统计/个性化，不拦截) ---
    current_user = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = MyJWT.decode_token(token)
            current_user = await db.get(UserAuth, int(payload.get("sub")))
        except:
            pass

    # --- 业务调用 ---
    result = await CarESService.search_cars_pro(params)

    return {
        "code": 200,
        "msg": "success",
        "data": result,
        "meta": {
            "user": current_user.username if current_user else "guest"
        }
    }