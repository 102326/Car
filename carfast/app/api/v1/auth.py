# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request  # <--- 新增 Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import LoginRequest
from app.services.auth.factory import AuthFactory
from app.utils.jwt import MyJWT
# ✅ 引入任务
from app.tasks.auth_tasks import send_login_notification, analyze_login_risk

router = APIRouter()


@router.post("/login", summary="统一登录接口 (策略模式 + EDA)")
async def login(
        body: LoginRequest,  # 注意：这里改名叫 body，避免和 request 冲突
        request: Request,  # <--- 注入 Request 对象获取 IP
        db: AsyncSession = Depends(get_db)
):
    try:
        # 1. 找策略
        strategy = AuthFactory.get_strategy(body.login_type)

        # 2. 认身份
        user = await strategy.authenticate(body.payload, db)

        # 3. 发令牌
        access_token, refresh_token = await MyJWT.login_user(user.id)

        # ==========================================
        # 4. 广播事件 (EDA - Fire and Forget)
        # ==========================================
        client_ip = request.client.host

        # 🚀 关键：这里使用 .delay()，它是瞬间完成的，不会阻塞主线程
        # 任务 1: 发通知
        send_login_notification.delay(
            user_id=user.id,
            login_type=body.login_type,
            ip=client_ip
        )

        # 任务 2: 做风控
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