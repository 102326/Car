# app/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.utils.jwt import MyJWT
from app.models.user import User

# 定义 Token 获取路径，FastAPI 文档的 "Authorize" 按钮会用到
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    依赖注入函数：验证 Token -> 检查黑名单 -> 查数据库 -> 返回 User 对象
    """
    # 1. 解码
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

    # 5. 查数据库
    user = await User.get_or_none(id=int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")

    return user