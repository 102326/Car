# app/services/auth/strategies/sms.py
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth.base import AuthStrategy
from app.models.user import UserAuth, UserProfile
from app.utils.jwt import redis_client  # 复用现有 Redis 连接


class SmsStrategy(AuthStrategy):
    async def authenticate(self, payload: dict, db: AsyncSession) -> UserAuth:
        phone = payload.get("phone")
        code = payload.get("code")

        if not phone or not code:
            raise HTTPException(status_code=400, detail="手机号或验证码不能为空")

        # 1. Redis 校验逻辑
        redis_key = f"sms:code:{phone}"

        # --- 开发后门：输入 8888 直接过 ---
        if code == "8888":
            pass
        else:
            cached_code = await redis_client.get(redis_key)
            if not cached_code or cached_code != code:
                raise HTTPException(status_code=400, detail="验证码错误或已失效")
            await redis_client.delete(redis_key)  # 防重放

        # 2. 查库或自动注册
        stmt = select(UserAuth).where(UserAuth.phone == phone)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # 自动注册逻辑
            print(f"🚀 [Auth] 新用户注册: {phone}")
            user = UserAuth(phone=phone, status=1)
            db.add(user)
            await db.flush()  # 获取 ID

            # 顺便初始化 Profile
            profile = UserProfile(user_id=user.id, nickname=f"用户{phone[-4:]}")
            db.add(profile)
            await db.flush()

        if user.status != 1:
            raise HTTPException(status_code=403, detail="账号已被禁用")

        return user