# app/services/auth/strategies/password.py
from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth.base import AuthStrategy
from app.models.user import UserAuth
from app.utils.security import verify_password


class PasswordStrategy(AuthStrategy):
    async def authenticate(self, payload: dict, db: AsyncSession) -> UserAuth:
        account = payload.get("account")  # 前端传 "account"
        password = payload.get("password")

        if not account or not password:
            raise HTTPException(status_code=400, detail="账号或密码不能为空")

        # 1. 查库：同时匹配手机号或邮箱
        stmt = select(UserAuth).where(
            or_(UserAuth.phone == account, UserAuth.email == account),
            UserAuth.status == 1
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        # 2. 验密：Argon2 算法
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            # 模糊报错，防止枚举攻击
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账号或密码错误"
            )

        return user