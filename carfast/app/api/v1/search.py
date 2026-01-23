from fastapi import APIRouter, Request, Header
# ❌ 彻底移除 DB 相关依赖
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.core.database import get_db
# from app.models.user import UserAuth
from app.services.es_service import CarESService
from app.schemas.search import SearchParams
from app.utils.jwt import MyJWT
from typing import Optional

router = APIRouter()


@router.post("/cars", summary="[Pro] 高级搜索接口 (纯净版)")
async def search_cars_pro(
        request: Request,
        params: SearchParams,
        # ✅ 核心改动：移除 db: AsyncSession 依赖
        # 这意味着请求进来时，FastAPI 不会去触碰数据库连接池
        authorization: Optional[str] = Header(None)
):
    """
    极致性能搜索接口:
    1. 纯 CPU 运算 (JWT 解析)
    2. 纯 ES I/O (数据检索)
    3. 零 PGSQL 压力 (Stateless)
    """

    # --- 1. Stateless 鉴权 (纯 CPU) ---
    current_user_id = None
    user_role = "guest"

    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ")[1]
            # 这里只做 CPU 密文解码和签名校验，不查库
            payload = MyJWT.decode_token(token)

            # 直接从 Token 里拿数据 (Phase 2 的 JWT 必须包含这些信息)
            current_user_id = payload.get("sub")
            user_role = payload.get("role", "user")
        except Exception as e:
            # Token 无效不阻断搜索，降级为游客
            print(f"Token decode failed: {e}")
            pass

    user_identity = f"会员({current_user_id})" if current_user_id else "游客"

    # 打印日志 (实际生产中建议用 logger)
    # 此时我们已经知道是谁在搜，但完全没用数据库
    print(f"🚀 [{user_identity} | Role:{user_role}] 执行搜索: {params.dict()}")

    # --- 2. 纯 ES 查询 ---
    # 如果未来需要针对 user_id 做个性化排序，直接把 id 传给 ES Service
    # 让 ES 去处理，而不是在这里查 PG
    result = await CarESService.search_cars_pro(params)

    return {
        "code": 200,
        "msg": "success",
        "data": result,
        "meta": {
            "identity": user_identity,
            "latency_source": "Elasticsearch Only"  # 标记数据源
        }
    }