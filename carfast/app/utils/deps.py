"""
依赖注入模块 (SQLAlchemy 2.0 版本)
提供用户认证、权限验证等依赖函数
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.utils.jwt import MyJWT
from app.models.user import UserAuth

# ==========================================
# OAuth2 Token 方案配置
# ==========================================
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    scheme_name="JWT",
    description="JWT Token 认证"
)

# 可选的 OAuth2 方案（允许匿名访问）
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False  # 不自动抛出 401 错误
)


# ==========================================
# 核心依赖函数
# ==========================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserAuth:
    """
    获取当前登录用户（必须登录）
    
    依赖注入函数：验证 Token -> 检查黑名单 -> 查数据库 -> 返回 UserAuth 对象
    
    Args:
        token: JWT Access Token
        db: 数据库会话
        
    Returns:
        UserAuth: 当前登录用户对象（不包含关联数据）
        
    Raises:
        HTTPException 401: Token 无效、过期、或在黑名单中
        HTTPException 404: 用户不存在
        HTTPException 403: 用户已被禁用或注销
        
    Example:
        ```python
        @router.get("/profile")
        async def get_profile(
            current_user: UserAuth = Depends(get_current_user)
        ):
            return {"user_id": current_user.id}
        ```
    """
    # 1. 解码 Token（会自动验证签名和过期时间）
    payload = MyJWT.decode_token(token)

    # 2. 检查 Token 类型
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token类型错误：需要Access Token"
        )

    # 3. 检查 Redis 黑名单（处理登出/踢人逻辑）
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Token：缺少JTI"
        )
    
    if await MyJWT.is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token已失效（用户已登出或在其他设备登录）"
        )

    # 4. 获取用户ID
    user_id_str = payload.get("sub")  # JWT 标准字段
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Token载荷：缺少用户ID"
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Token载荷：用户ID格式错误"
        )

    # 5. 查询数据库
    result = await db.execute(
        select(UserAuth).where(UserAuth.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在（可能已被删除）"
        )

    # 6. 检查用户状态
    # status: 1=正常, 0=禁用, 2=注销
    if user.status == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员"
        )
    elif user.status == 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已注销"
        )
    elif user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"账号状态异常：{user.status}"
        )

    return user


async def get_current_user_with_profile(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserAuth:
    """
    获取当前登录用户（包含 Profile 信息）
    
    使用场景：需要展示用户昵称、头像等信息的接口
    
    Args:
        token: JWT Access Token
        db: 数据库会话
        
    Returns:
        UserAuth: 当前登录用户对象（已预加载 profile 关联）
        
    Example:
        ```python
        @router.get("/me")
        async def get_me(
            current_user: UserAuth = Depends(get_current_user_with_profile)
        ):
            return {
                "user_id": current_user.id,
                "nickname": current_user.profile.nickname,
                "avatar": current_user.profile.avatar_url
            }
        ```
    """
    # 复用基础验证逻辑
    payload = MyJWT.decode_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token类型错误"
        )
    
    jti = payload.get("jti")
    if await MyJWT.is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token已失效"
        )
    
    user_id = int(payload.get("sub"))
    
    # 查询用户并预加载 Profile
    result = await db.execute(
        select(UserAuth)
        .options(selectinload(UserAuth.profile))  # 预加载关联
        .where(UserAuth.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账号已被禁用或注销")
    
    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[UserAuth]:
    """
    获取当前用户（可选，允许匿名访问）
    
    使用场景：
    - 内容详情页（登录用户可以点赞，未登录只能浏览）
    - 商品列表（登录用户显示收藏状态）
    
    Args:
        token: JWT Access Token（可选）
        db: 数据库会话
        
    Returns:
        Optional[UserAuth]: 登录则返回用户对象，未登录返回 None
        
    Example:
        ```python
        @router.get("/posts/{post_id}")
        async def get_post(
            post_id: int,
            current_user: Optional[UserAuth] = Depends(get_optional_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            post = await get_post_by_id(post_id, db)
            
            # 如果登录，返回是否已点赞
            if current_user:
                post.is_liked = await check_user_liked(current_user.id, post_id, db)
            
            return post
        ```
    """
    if not token:
        return None
    
    try:
        payload = MyJWT.decode_token(token)
        
        if payload.get("type") != "access":
            return None
        
        jti = payload.get("jti")
        if await MyJWT.is_token_revoked(jti):
            return None
        
        user_id = int(payload.get("sub"))
        
        result = await db.execute(
            select(UserAuth).where(UserAuth.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user and user.status == 1:
            return user
        
    except Exception:
        # 任何验证失败都返回 None，不抛出错误
        pass
    
    return None


async def require_dealer(
    current_user: UserAuth = Depends(get_current_user_with_profile)
) -> UserAuth:
    """
    要求用户必须是认证经销商
    
    使用场景：经销商专属功能（发布车源、管理库存等）
    
    Args:
        current_user: 当前登录用户
        
    Returns:
        UserAuth: 经销商用户对象
        
    Raises:
        HTTPException 403: 用户不是认证经销商
        
    Example:
        ```python
        @router.post("/dealer/cars")
        async def add_car(
            car_data: CarCreate,
            dealer: UserAuth = Depends(require_dealer)
        ):
            # 只有认证经销商可以访问
            return await create_car(car_data, dealer.id)
        ```
    """
    if not current_user.profile or not current_user.profile.is_dealer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限认证经销商访问，请先完成经销商认证"
        )
    
    return current_user


async def require_verified(
    current_user: UserAuth = Depends(get_current_user)
) -> UserAuth:
    """
    要求用户必须通过实名认证
    
    使用场景：敏感操作（下单、卖车、金融服务等）
    
    Args:
        current_user: 当前登录用户
        
    Returns:
        UserAuth: 已实名认证的用户对象
        
    Raises:
        HTTPException 403: 用户未完成实名认证
        
    Example:
        ```python
        @router.post("/orders")
        async def create_order(
            order_data: OrderCreate,
            verified_user: UserAuth = Depends(require_verified)
        ):
            # 只有实名用户可以下单
            return await place_order(order_data, verified_user.id)
        ```
    """
    # 检查是否有实名认证记录（需要预加载关联）
    # 如果没有预加载，这里需要额外查询
    # 为了性能，建议在路由中使用 selectinload(UserAuth.realname)
    
    # 简化版本：只检查是否有关联数据
    # 完整版本需要检查 verify_status == 1
    if not hasattr(current_user, 'realname') or not current_user.realname:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先完成实名认证"
        )
    
    if current_user.realname.verify_status != 1:
        status_text = {
            0: "实名认证审核中",
            2: "实名认证被驳回"
        }.get(current_user.realname.verify_status, "实名认证状态异常")
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=status_text
        )
    
    return current_user