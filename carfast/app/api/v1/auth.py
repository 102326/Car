import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import LoginParam, Token, UserInfo
from app.services.auth.factory import AuthFactory
from app.utils.jwt import MyJWT
from app.models.user import UserAuth
# 引入 Celery 任务
from app.tasks.auth_tasks import (
    send_sms_code_task,
    send_login_notification,
    analyze_login_risk
)

router = APIRouter()
logger = logging.getLogger(__name__)


# --- 新增：发送验证码接口 ---
@router.post("/sms", summary="发送短信验证码")
async def send_sms_code(
    phone: str,
):
    """
    前端点击'获取验证码'时调用此接口
    """
    mock_code = "8888"
    logger.info(f"📱 收到发送验证码请求: {phone}")

    # 触发 P1 级 Celery 任务
    send_sms_code_task.delay(phone, mock_code)

    return {"code": 200, "msg": "验证码已发送 (测试环境默认为 8888)"}


@router.post("/login", response_model=Token, summary="统一登录接口")
async def login(
    request: Request,
    param: LoginParam,  # 使用新的 LoginParam 模型
    db: AsyncSession = Depends(get_db)
):
    """
    支持多种登录方式 (策略模式):
    - password: 账号密码
    - sms: 手机号验证码
    - dingtalk: 钉钉免登
    """
    # 1. 获取对应的登录策略
    strategy = AuthFactory.get_strategy(param.login_type)
    if not strategy:
        raise HTTPException(status_code=400, detail=f"不支持的登录方式: {param.login_type}")

    # 2. 执行登录认证 (返回 User 对象)
    # ✅ [修正点 1] 使用 model_dump() 替代 .dict() (Pydantic v2)
    # ✅ [修正点 2] 修正参数顺序：先传 payload (dict)，再传 db (AsyncSession)
    #    对应 base.py: authenticate(self, payload: dict, db: AsyncSession)
    payload = param.model_dump()
    user = await strategy.authenticate(payload, db)

    if not user:
        raise HTTPException(status_code=401, detail="认证失败")

    # 3. 签发 JWT
    access_token = MyJWT.create_token(str(user.id))

    # 4. 获取客户端 IP (用于风控)
    client_ip = request.client.host if request.client else "unknown"

    # 5. 触发异步副作用任务 (Celery)
    logger.info(f"🚀 登录成功，触发异步任务 -> User: {user.id}")

    # Task A: 发送登录通知 (P2 低优队列)
    send_login_notification.delay(
        user_id=user.id,
        login_type=param.login_type,
        ip=client_ip
    )

    # Task B: 触发风控分析 (P1 高优队列)
    analyze_login_risk.delay(
        user_id=user.id,
        ip=client_ip
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_name": user.username or user.phone or "未命名用户"
    }


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    需要 Header 携带 Authorization: Bearer <token>
    """
    # 1. 解析 Token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    token = auth_header.split(" ")[1]
    try:
        payload = MyJWT.decode_token(token)
        user_id = int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Token 无效")

    # 2. 查询数据库
    user = await db.get(UserAuth, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 3. 构造返回
    display_name = f"用户{user.phone[-4:]}" if user.phone else "匿名用户"

    return {
        "id": user.id,
        "username": user.username,
        "nickname": getattr(user, "nickname", display_name),
        "avatar": user.avatar,
        "roles": ["user"]
    }