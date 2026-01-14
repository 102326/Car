# app/utils/deps.py
from typing import AsyncGenerator
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.utils.jwt import MyJWT
from app.models.user import UserAuth

# 定义 Token 获取路径，FastAPI 文档的 "Authorize" 按钮会用到
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserAuth:
    """
    依赖注入函数：验证 Token -> 检查黑名单 -> 查数据库 -> 返回 UserAuth 对象
    
    Args:
        token: JWT Token
        db: 数据库会话
        
    Returns:
        UserAuth: 当前登录用户对象
        
    Raises:
        HTTPException: Token 无效或用户不存在
    """
    # 1. 解码 Token
    payload = MyJWT.decode_token(token)

    # 2. 检查是否是 Access Token
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token类型错误")

    # 3. 检查 Redis 黑名单
    jti = payload.get("jti")
    if await MyJWT.is_token_revoked(jti):
        raise HTTPException(status_code=401, detail="Token已失效(被登出或在其他设备登录)")

    # 4. 获取 UserID
    user_id = payload.get("sub")  # 对应 MyJWT.encode 里的 key
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的Token载荷")

    # 5. 查数据库 (SQLAlchemy 方式)
    result = await db.execute(
        select(UserAuth).where(UserAuth.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 6. 检查用户状态（status: 1=正常, 0=禁用, 2=注销）
    if user.status != 1:
        raise HTTPException(status_code=400, detail="用户已被禁用或注销")

    return user