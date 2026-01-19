# app/api/v1/search.py
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
# ✅ 修正：导入你现有的 CarESService
from app.services.es_service import CarESService
from app.utils.jwt import MyJWT
from app.models.user import UserAuth

router = APIRouter()


@router.get("/cars", summary="全站搜索 (混合模式)")
async def search_cars(
        request: Request,
        q: str = Query(..., min_length=1, description="搜索关键词"),
        page: int = 1,
        size: int = 10,
        db: AsyncSession = Depends(get_db)
):
    # --- 1. 手动柔性鉴权 (保持不变) ---
    current_user = None
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = MyJWT.decode_token(token)
            user_id = int(payload.get("sub"))
            current_user = await db.get(UserAuth, user_id)
        except Exception:
            pass

    # --- 2. 业务逻辑 ---
    user_identity = "游客"
    if current_user:
        user_identity = f"会员({current_user.phone})"

    print(f"🔍 [{user_identity}] 正在搜索: {q}")

    # ✅ 修正：调用 CarESService
    result = await CarESService.search_cars(q, page, size)

    return {
        "code": 200,
        "msg": "success",
        "data": result,
        "meta": {
            "identity": user_identity,
            "is_authenticated": bool(current_user)
        }
    }