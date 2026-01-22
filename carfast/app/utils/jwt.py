"""
JWT Token 工具模块
提供 Token 生成、验证、刷新、黑名单管理等功能

特性：
- 支持 Access Token 和 Refresh Token
- 基于 Redis 的黑名单机制（实现登出和踢人）
- 单点登录控制（同一用户只能在一个设备登录）
- 符合 JWT 标准（使用 'sub' 存储用户ID）
"""
import jwt
import uuid
import datetime
from datetime import timedelta, timezone
import redis.asyncio as redis
from typing import Tuple, Optional, Dict, Any
from fastapi import HTTPException, status

from app.config import settings


# ==========================================
# Redis 连接池初始化
# ==========================================
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,  # 最大连接数
    socket_timeout=5,    # 超时时间
    socket_connect_timeout=5
)
redis_client = redis.Redis(connection_pool=redis_pool)




# ==========================================
# JWT 工具类
# ==========================================

class MyJWT:
    """JWT Token 管理工具类"""
    
    # Token 过期时间配置
    ACCESS_TOKEN_EXPIRE = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    REFRESH_TOKEN_EXPIRE = timedelta(days=7)
    
    # Redis Key 前缀
    BLACKLIST_PREFIX = "jwt:blacklist:"
    USER_ACTIVE_PREFIX = "jwt:user_active:"
    
    @staticmethod
    def _generate_jti() -> str:
        """
        生成唯一的 JWT ID (JTI)
        
        Returns:
            str: UUID 字符串
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def encode(
        payload: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        编码 JWT Token
        
        Args:
            payload: Token 载荷数据（必须包含 'sub' 用户ID）
            expires_delta: 过期时间增量（不传则使用默认配置）
            
        Returns:
            str: JWT Token 字符串
            
        Example:
            ```python
            token = MyJWT.encode(
                {"sub": "123", "type": "access"},
                expires_delta=timedelta(hours=1)
            )
            ```
        """
        to_encode = payload.copy()
        now = datetime.datetime.now(timezone.utc)
        
        # 设置过期时间
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + MyJWT.ACCESS_TOKEN_EXPIRE
        
        # 添加标准 JWT 字段
        to_encode.update({
            "exp": expire,  # 过期时间
            "iat": now,     # 签发时间
            "jti": to_encode.get("jti") or MyJWT._generate_jti()  # JWT ID
        })
        
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        解码 JWT Token
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            Dict[str, Any]: Token 载荷数据
            
        Raises:
            HTTPException 401: Token 过期或无效
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token已过期，请重新登录",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"无效的Token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )

    @staticmethod
    async def is_token_revoked(jti: str) -> bool:
        """
        检查 Token 是否在黑名单中
        
        Args:
            jti: JWT ID
            
        Returns:
            bool: True=已吊销，False=未吊销
        """
        key = f"{MyJWT.BLACKLIST_PREFIX}{jti}"
        return await redis_client.exists(key) > 0
    
    @staticmethod
    async def add_to_blacklist(jti: str, expires_seconds: int) -> None:
        """
        将 Token 加入黑名单
        
        Args:
            jti: JWT ID
            expires_seconds: 过期秒数（建议与 Token 剩余有效期一致）
        """
        if expires_seconds > 0:
            key = f"{MyJWT.BLACKLIST_PREFIX}{jti}"
            await redis_client.setex(key, expires_seconds, "revoked")

    @staticmethod
    async def login_user(user_id: int) -> Tuple[str, str]:
        """
        用户登录：生成 Token 并实现单点登录（踢掉旧会话）
        
        策略：同一用户只能在一个设备登录
        如需多端登录，请注释掉"拉黑旧Token"部分
        
        Args:
            user_id: 用户ID
            
        Returns:
            Tuple[str, str]: (access_token, refresh_token)
            
        Example:
            ```python
            access_token, refresh_token = await MyJWT.login_user(user.id)
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
            ```
        """
        user_key = f"{MyJWT.USER_ACTIVE_PREFIX}{user_id}"
        
        # 1. 获取旧 Token（用于踢人）
        old_access_jti = await redis_client.hget(user_key, "access_jti")
        old_refresh_jti = await redis_client.hget(user_key, "refresh_jti")
        
        # 2. 拉黑旧 Token（实现单点登录）
        # ⚠️ 如果需要多端登录（手机+电脑），请注释掉这部分
        if old_access_jti:
            await MyJWT.add_to_blacklist(
                old_access_jti,
                int(MyJWT.ACCESS_TOKEN_EXPIRE.total_seconds())
            )
        if old_refresh_jti:
            await MyJWT.add_to_blacklist(
                old_refresh_jti,
                int(MyJWT.REFRESH_TOKEN_EXPIRE.total_seconds())
            )
        
        # 3. 生成新 Token
        access_jti = MyJWT._generate_jti()
        refresh_jti = MyJWT._generate_jti()
        
        access_token = MyJWT.encode(
            {
                "sub": str(user_id),
                "type": "access",
                "jti": access_jti
            },
            expires_delta=MyJWT.ACCESS_TOKEN_EXPIRE
        )
        
        refresh_token = MyJWT.encode(
            {
                "sub": str(user_id),
                "type": "refresh",
                "jti": refresh_jti
            },
            expires_delta=MyJWT.REFRESH_TOKEN_EXPIRE
        )
        
        # 4. 存入 Redis（记录活跃会话）
        await redis_client.hset(user_key, mapping={
            "access_jti": access_jti,
            "refresh_jti": refresh_jti,
            "login_at": datetime.datetime.now(timezone.utc).isoformat()
        })
        await redis_client.expire(user_key, MyJWT.REFRESH_TOKEN_EXPIRE)
        
        return access_token, refresh_token

    @staticmethod
    async def refresh_access_token(
        refresh_token_str: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        刷新 Access Token
        
        使用 Refresh Token 换取新的 Access Token
        
        Args:
            refresh_token_str: Refresh Token 字符串
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (新的access_token, 错误信息)
            - 成功: (token, None)
            - 失败: (None, error_message)
            
        Example:
            ```python
            new_token, error = await MyJWT.refresh_access_token(refresh_token)
            if error:
                raise HTTPException(401, detail=error)
            return {"access_token": new_token}
            ```
        """
        try:
            payload = jwt.decode(
                refresh_token_str,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            return None, "Refresh Token 已过期，请重新登录"
        except jwt.InvalidTokenError:
            return None, "无效的 Refresh Token"
        
        # 验证 Token 类型
        if payload.get("type") != "refresh":
            return None, "Token 类型错误：需要 Refresh Token"
        
        user_id = payload.get("sub")
        jti = payload.get("jti")
        
        if not user_id or not jti:
            return None, "Token 载荷不完整"
        
        # 检查黑名单
        if await MyJWT.is_token_revoked(jti):
            return None, "Refresh Token 已失效"
        
        # 验证是否是当前活跃会话
        user_key = f"{MyJWT.USER_ACTIVE_PREFIX}{user_id}"
        active_refresh_jti = await redis_client.hget(user_key, "refresh_jti")
        
        if active_refresh_jti != jti:
            return None, "Refresh Token 已过时（可能在其他设备登录了）"
        
        # 签发新 Access Token
        new_access_jti = MyJWT._generate_jti()
        new_access_token = MyJWT.encode(
            {
                "sub": str(user_id),
                "type": "access",
                "jti": new_access_jti
            },
            expires_delta=MyJWT.ACCESS_TOKEN_EXPIRE
        )
        
        # 更新 Redis 中的 Access JTI
        await redis_client.hset(user_key, "access_jti", new_access_jti)
        
        return new_access_token, None
    
    @staticmethod
    async def logout_user(user_id: int) -> None:
        """
        用户登出：吊销所有 Token
        
        Args:
            user_id: 用户ID
            
        Example:
            ```python
            @router.post("/logout")
            async def logout(current_user: UserAuth = Depends(get_current_user)):
                await MyJWT.logout_user(current_user.id)
                return {"message": "登出成功"}
            ```
        """
        user_key = f"{MyJWT.USER_ACTIVE_PREFIX}{user_id}"
        
        # 获取当前活跃的 Token
        access_jti = await redis_client.hget(user_key, "access_jti")
        refresh_jti = await redis_client.hget(user_key, "refresh_jti")
        
        # 加入黑名单
        if access_jti:
            await MyJWT.add_to_blacklist(
                access_jti,
                int(MyJWT.ACCESS_TOKEN_EXPIRE.total_seconds())
            )
        if refresh_jti:
            await MyJWT.add_to_blacklist(
                refresh_jti,
                int(MyJWT.REFRESH_TOKEN_EXPIRE.total_seconds())
            )
        
        # 删除 Redis 记录
        await redis_client.delete(user_key)
    
    @staticmethod
    async def revoke_current_tokens(user_id: int) -> None:
        """
        吊销当前 Token（logout_user 的别名）
        
        Args:
            user_id: 用户ID
        """
        await MyJWT.logout_user(user_id)
    
    @staticmethod
    async def get_active_session_info(user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户活跃会话信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 会话信息（login_at等）
        """
        user_key = f"{MyJWT.USER_ACTIVE_PREFIX}{user_id}"
        data = await redis_client.hgetall(user_key)
        
        if not data:
            return None
        
        return {
            "login_at": data.get("login_at"),
            "has_active_session": True
        }