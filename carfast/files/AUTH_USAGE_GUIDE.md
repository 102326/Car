# 🔐 认证系统使用指南

## 📋 概述

CarFast 认证系统基于 **JWT Token** + **Redis 黑名单** 实现，提供完整的用户认证、授权和会话管理功能。

### 核心特性

✅ **JWT Token 认证**（Access Token + Refresh Token）  
✅ **单点登录**（同一用户只能在一个设备登录）  
✅ **Token 黑名单**（基于 Redis 实现登出和踢人）  
✅ **密码加密**（Argon2 算法）  
✅ **角色权限**（经销商、实名用户）  
✅ **可选认证**（支持匿名访问）

---

## 📦 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **依赖注入** | `app/utils/deps.py` | 提供各种用户认证依赖函数 |
| **JWT 工具** | `app/utils/jwt.py` | Token 生成、验证、刷新 |
| **密码工具** | `app/utils/security.py` | 密码哈希、验证 |
| **用户模型** | `app/models/user.py` | UserAuth, UserProfile 等 |

---

## 🚀 快速开始

### 1️⃣ 用户注册

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.user import UserAuth, UserProfile
from app.utils.security import get_password_hash, check_password_strength

router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    phone: str
    password: str
    nickname: str = "易车用户"


@router.post("/register")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    
    # 1. 检查手机号是否已注册
    result = await db.execute(
        select(UserAuth).where(UserAuth.phone == request.phone)
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "手机号已注册")
    
    # 2. 验证密码强度
    is_valid, error = check_password_strength(request.password)
    if not is_valid:
        raise HTTPException(400, error)
    
    # 3. 创建用户
    user = UserAuth(
        phone=request.phone,
        password_hash=get_password_hash(request.password),
        status=1
    )
    db.add(user)
    await db.flush()  # 获取 user.id
    
    # 4. 创建用户资料
    profile = UserProfile(
        user_id=user.id,
        nickname=request.nickname
    )
    db.add(profile)
    await db.commit()
    
    return {
        "user_id": user.id,
        "message": "注册成功"
    }
```

---

### 2️⃣ 用户登录

```python
from app.utils.jwt import MyJWT
from app.utils.security import verify_password


class LoginRequest(BaseModel):
    phone: str
    password: str


@router.post("/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    
    # 1. 查询用户
    result = await db.execute(
        select(UserAuth).where(UserAuth.phone == request.phone)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(401, "手机号或密码错误")
    
    # 2. 验证密码
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(401, "手机号或密码错误")
    
    # 3. 检查账号状态
    if user.status != 1:
        raise HTTPException(403, "账号已被禁用或注销")
    
    # 4. 生成 Token（会自动踢掉旧会话）
    access_token, refresh_token = await MyJWT.login_user(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.id
    }
```

---

### 3️⃣ 获取当前用户信息

```python
from app.utils.deps import get_current_user, get_current_user_with_profile
from app.models.user import UserAuth


@router.get("/me")
async def get_current_user_info(
    current_user: UserAuth = Depends(get_current_user_with_profile)
):
    """获取当前用户信息（需要登录）"""
    return {
        "user_id": current_user.id,
        "phone": current_user.phone,
        "nickname": current_user.profile.nickname,
        "avatar": current_user.profile.avatar_url,
        "level": current_user.profile.level,
        "is_dealer": current_user.profile.is_dealer
    }
```

---

### 4️⃣ 刷新 Token

```python
class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """刷新 Access Token"""
    
    new_access_token, error = await MyJWT.refresh_access_token(
        request.refresh_token
    )
    
    if error:
        raise HTTPException(401, detail=error)
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }
```

---

### 5️⃣ 用户登出

```python
@router.post("/logout")
async def logout(
    current_user: UserAuth = Depends(get_current_user)
):
    """用户登出"""
    
    await MyJWT.logout_user(current_user.id)
    
    return {"message": "登出成功"}
```

---

## 🎯 依赖函数使用场景

### 场景1：必须登录的接口

```python
from app.utils.deps import get_current_user

@router.get("/orders")
async def get_my_orders(
    current_user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """查询我的订单（必须登录）"""
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id)
    )
    return result.scalars().all()
```

---

### 场景2：需要用户资料的接口

```python
from app.utils.deps import get_current_user_with_profile

@router.post("/posts")
async def create_post(
    post_data: PostCreate,
    current_user: UserAuth = Depends(get_current_user_with_profile),
    db: AsyncSession = Depends(get_db)
):
    """发布帖子（需要昵称等信息）"""
    post = CMSPost(
        user_id=current_user.id,
        title=post_data.title,
        content_body=post_data.content,
        # 可以直接访问 profile
        author_nickname=current_user.profile.nickname,
        author_avatar=current_user.profile.avatar_url
    )
    db.add(post)
    await db.commit()
    return post
```

---

### 场景3：可选登录的接口

```python
from app.utils.deps import get_optional_current_user

@router.get("/posts/{post_id}")
async def get_post_detail(
    post_id: int,
    current_user: Optional[UserAuth] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """帖子详情（登录用户可以看到是否已点赞）"""
    
    # 查询帖子
    result = await db.execute(
        select(CMSPost).where(CMSPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(404, "帖子不存在")
    
    response = {
        "id": post.id,
        "title": post.title,
        "content": post.content_body,
        "view_count": post.view_count,
        "like_count": post.like_count
    }
    
    # 如果用户已登录，查询是否已点赞
    if current_user:
        result = await db.execute(
            select(PostLike).where(
                PostLike.post_id == post_id,
                PostLike.user_id == current_user.id
            )
        )
        response["is_liked"] = result.scalar_one_or_none() is not None
    else:
        response["is_liked"] = False
    
    return response
```

---

### 场景4：只允许经销商访问

```python
from app.utils.deps import require_dealer

@router.post("/dealer/cars")
async def add_dealer_car(
    car_data: CarCreate,
    dealer: UserAuth = Depends(require_dealer),
    db: AsyncSession = Depends(get_db)
):
    """添加车源（仅限经销商）"""
    
    # dealer.profile.is_dealer 已在依赖中验证为 True
    car = DealerCar(
        dealer_id=dealer.id,
        brand=car_data.brand,
        model=car_data.model,
        price=car_data.price
    )
    db.add(car)
    await db.commit()
    return car
```

---

### 场景5：只允许实名用户访问

```python
from app.utils.deps import require_verified

@router.post("/orders")
async def create_order(
    order_data: OrderCreate,
    verified_user: UserAuth = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    """创建订单（必须实名认证）"""
    
    # verified_user.realname.verify_status == 1 已验证
    order = Order(
        user_id=verified_user.id,
        real_name=verified_user.realname.real_name,
        total_amount=order_data.amount
    )
    db.add(order)
    await db.commit()
    return order
```

---

## 🔧 前端对接

### 1. 登录流程

```typescript
// 1. 用户登录
const loginResponse = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    phone: '13800138000',
    password: 'Test@1234'
  })
})

const { access_token, refresh_token } = await loginResponse.json()

// 2. 存储 Token
localStorage.setItem('access_token', access_token)
localStorage.setItem('refresh_token', refresh_token)
```

---

### 2. 请求拦截器（自动添加 Token）

```typescript
// Axios 示例
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

---

### 3. 响应拦截器（自动刷新 Token）

```typescript
axios.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config
    
    // 如果是 401 且未重试过
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        // 刷新 Token
        const refreshToken = localStorage.getItem('refresh_token')
        const response = await axios.post('/api/auth/refresh', {
          refresh_token: refreshToken
        })
        
        const { access_token } = response.data
        localStorage.setItem('access_token', access_token)
        
        // 重试原请求
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return axios(originalRequest)
        
      } catch (refreshError) {
        // 刷新失败，跳转登录页
        localStorage.clear()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)
```

---

## 🛡️ 安全建议

### 1. Token 存储

**推荐方案**：
- ✅ Access Token 存 `localStorage`（方便读取）
- ✅ Refresh Token 存 `httpOnly Cookie`（更安全）

**不推荐**：
- ❌ 敏感信息存 `localStorage`（易被 XSS 攻击）

---

### 2. 密码策略

```python
# 强制密码强度检查
is_valid, error = check_password_strength(password)
if not is_valid:
    raise HTTPException(400, error)

# 密码规则：
# - 长度至少 8 位
# - 包含大小写字母
# - 包含数字
# - 建议包含特殊字符
```

---

### 3. 登录失败限制

```python
# TODO: 建议添加登录失败次数限制
# 使用 Redis 记录失败次数，超过 5 次锁定 15 分钟

redis_key = f"login_fail:{phone}"
fail_count = await redis_client.incr(redis_key)
await redis_client.expire(redis_key, 900)  # 15分钟

if fail_count > 5:
    raise HTTPException(429, "登录失败次数过多，请15分钟后再试")
```

---

### 4. 敏感操作二次验证

```python
@router.post("/withdraw")
async def withdraw_money(
    amount: Decimal,
    sms_code: str,  # 短信验证码
    current_user: UserAuth = Depends(require_verified)
):
    """提现（需要短信验证）"""
    
    # 验证短信验证码
    if not await verify_sms_code(current_user.phone, sms_code):
        raise HTTPException(400, "验证码错误")
    
    # ... 处理提现逻辑
```

---

## 📊 会话管理

### 查看当前会话

```python
@router.get("/session")
async def get_session_info(
    current_user: UserAuth = Depends(get_current_user)
):
    """查看当前会话信息"""
    
    session_info = await MyJWT.get_active_session_info(current_user.id)
    return session_info or {"message": "无活跃会话"}
```

---

### 踢掉所有设备

```python
@router.post("/logout-all")
async def logout_all_devices(
    current_user: UserAuth = Depends(get_current_user)
):
    """登出所有设备"""
    
    await MyJWT.logout_user(current_user.id)
    return {"message": "已在所有设备登出"}
```

---

## ✅ 完整示例

参考文件：`app/views/auth.py`（示例路由）

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import UserAuth, UserProfile
from app.utils.deps import (
    get_current_user,
    get_current_user_with_profile,
    get_optional_current_user
)
from app.utils.jwt import MyJWT
from app.utils.security import get_password_hash, verify_password

router = APIRouter(prefix="/api/auth", tags=["认证"])

# ... 实现上面的所有路由
```

---

## 🎓 总结

✅ **deps.py**: 提供各种依赖函数  
✅ **jwt.py**: Token 生成和管理  
✅ **security.py**: 密码加密和验证  

现在您可以：
- 🔐 实现完整的用户认证流程
- 🛡️ 保护需要登录的接口
- 👥 区分不同角色权限
- 📱 支持单点登录和多端登录
- 🔄 自动刷新 Token

**祝开发顺利！** 🚀
