from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import LoginRequest
from app.services.auth.factory import AuthFactory
from app.utils.jwt import MyJWT
from app.tasks.auth_tasks import send_login_notification, analyze_login_risk
# ✅ 确保引入 UserAuth 和 依赖
from app.models.user import UserAuth
from app.utils.deps import get_current_user

router = APIRouter()


@router.post("/login", summary="统一登录接口 (策略模式 + EDA)")
async def login(
        body: LoginRequest,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    try:
        # 1. 找策略
        strategy = AuthFactory.get_strategy(body.login_type)

        # 2. 认身份
        user = await strategy.authenticate(body.payload, db)

        # 3. 发令牌
        access_token, refresh_token = await MyJWT.login_user(user.id)

        # 4. 广播事件 (EDA - Fire and Forget)
        client_ip = request.client.host
        send_login_notification.delay(
            user_id=user.id,
            login_type=body.login_type,
            ip=client_ip
        )
        analyze_login_risk.delay(
            user_id=user.id,
            ip=client_ip
        )

        return {
            "code": 200,
            "msg": "登录成功",
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "login_type": body.login_type,
                "user_id": user.id
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
        current_user: UserAuth = Depends(get_current_user),
):
    """
    根据 Token 获取当前登录用户的详细信息
    """
    # 1. 获取手机号 (UserAuth 中定义了 phone 字段)
    user_phone = current_user.phone

    # 2. 手机号脱敏处理 (例如: 138****0000)
    masked_phone = ""
    if user_phone and len(str(user_phone)) >= 11:
        p = str(user_phone)
        masked_phone = p[:3] + "****" + p[-4:]
    else:
        masked_phone = str(user_phone) if user_phone else "未知用户"

    # 3. 生成显示用的昵称
    # 既然 UserAuth 没有 username，我们用"用户+手机尾号"作为默认昵称
    display_name = f"用户{masked_phone[-4:]}" if user_phone else "易车新用户"

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "id": current_user.id,
            # 前端可能还在用 username 字段做兼容，我们把手机号传给它
            "username": user_phone,
            "phone": user_phone,
            "nickname": display_name,
            # 暂时给个默认头像
            "avatar": "https://img.yzcdn.cn/vant/cat.jpeg",
            "vip_level": 1,
            "vip_label": "普通会员"
        }
    }