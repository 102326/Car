# app/utils/jwt.py
import jwt
import uuid
import datetime
from datetime import timedelta, timezone
import redis.asyncio as redis
from typing import Tuple, Optional, Dict, Any
from fastapi import HTTPException, status

# 引入你之前建立的配置
from app.config import settings

# 初始化 Redis 连接池 (建议使用 config 中的 REDIS_URL)
redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
redis_client = redis.Redis(connection_pool=redis_pool)


class MyJWT:
    @staticmethod
    def _generate_jti():
        return str(uuid.uuid4())

    @staticmethod
    def encode(payload: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = payload.copy()
        now = datetime.datetime.now(timezone.utc)  # 修复 utcnow 废弃警告

        if expires_delta:
            expire = now + expires_delta
        else:
            # 使用 settings 配置
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "iat": now,
            "jti": to_encode.get("jti") or MyJWT._generate_jti()
        })

        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token已过期")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="无效的Token")

    @staticmethod
    async def is_token_revoked(jti: str) -> bool:
        return await redis_client.exists(f"blacklist:{jti}")

    @staticmethod
    async def add_to_blacklist(jti: str, expires_delta: int):
        if expires_delta > 0:
            await redis_client.setex(f"blacklist:{jti}", expires_delta, "revoked")

    @staticmethod
    async def login_user(user_id: int) -> Tuple[str, str]:
        """
        登录逻辑：会自动踢掉该用户之前的登录会话
        """
        user_key = f"user_active:{user_id}"

        # 1. 异步获取旧 Token
        old_access_jti = await redis_client.hget(user_key, "access_jti")
        old_refresh_jti = await redis_client.hget(user_key, "refresh_jti")

        # 2. 拉黑旧 Token (踢人策略)
        # 如果你想支持多端登录(手机电脑同时在线)，请注释掉这一段
        if old_access_jti:
            await MyJWT.add_to_blacklist(old_access_jti, 3600 * 24)
        if old_refresh_jti:
            await MyJWT.add_to_blacklist(old_refresh_jti, 3600 * 48)

        # 3. 生成新 Token
        access_jti = MyJWT._generate_jti()
        refresh_jti = MyJWT._generate_jti()

        access_token = MyJWT.encode(
            {"sub": str(user_id), "type": "access", "jti": access_jti},  # 建议用 sub 存 id，符合 JWT 标准
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = MyJWT.encode(
            {"sub": str(user_id), "type": "refresh", "jti": refresh_jti},
            expires_delta=timedelta(days=7)
        )

        # 4. 存入 Redis
        await redis_client.hset(user_key, mapping={
            "access_jti": access_jti,
            "refresh_jti": refresh_jti
        })
        await redis_client.expire(user_key, timedelta(days=7))

        return access_token, refresh_token

    @staticmethod
    async def refresh_access_token(refresh_token_str: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            # 1. 这里使用 settings.SECRET_KEY 是对的
            payload = jwt.decode(refresh_token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except Exception:
            return None, "无效的 Refresh Token"

        if payload.get("type") != "refresh":
            return None, "Token 类型错误"

        # 2. 这里获取 sub 是对的
        user_id = payload.get("sub")
        jti = payload.get("jti")

        if await MyJWT.is_token_revoked(jti):
            return None, "Refresh Token 已失效"

        user_key = f"user_active:{user_id}"
        active_refresh_jti = await redis_client.hget(user_key, "refresh_jti")

        if active_refresh_jti != jti:
            return None, "Refresh Token 已过时"

        # 签发新 Access Token
        new_access_jti = MyJWT._generate_jti()

        # === 【关键修改】 ===
        # 1. payload 的 key 必须是 "sub"，不能是 "user_id"，否则 deps.py 里的 get_current_user 读不到！
        # 2. 过期时间建议使用 settings 配置，而不是写死 30 分钟，保持一致性。
        new_access_token = MyJWT.encode(
            {"sub": str(user_id), "type": "access", "jti": new_access_jti},  # 修改这里：user_id -> sub
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)  # 建议修改：使用配置
        )

        # 更新 Redis 里的 Access JTI
        await redis_client.hset(user_key, "access_jti", new_access_jti)

        return new_access_token, None

    @staticmethod
    async def revoke_current_tokens(user_id: int):
        # 这个方法逻辑没问题，直接用即可
        user_key = f"user_active:{user_id}"
        access_jti = await redis_client.hget(user_key, "access_jti")
        refresh_jti = await redis_client.hget(user_key, "refresh_jti")

        if access_jti:
            await MyJWT.add_to_blacklist(access_jti, 3600 * 24)
        if refresh_jti:
            await MyJWT.add_to_blacklist(refresh_jti, 3600 * 48)

        await redis_client.delete(user_key)