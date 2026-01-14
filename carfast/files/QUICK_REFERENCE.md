# 🚀 SQLAlchemy 2.0 快速参考卡片

## 📦 导入

```python
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from fastapi import Depends
from app.database import get_db
from app.models.user import UserAuth, UserProfile
```

---

## 🔍 查询 (SELECT)

### 基础查询

```python
# 查询所有
result = await db.execute(select(UserAuth))
users = result.scalars().all()

# 查询单个
result = await db.execute(select(UserAuth).where(UserAuth.id == 1))
user = result.scalar_one_or_none()

# 带条件
result = await db.execute(
    select(UserAuth)
    .where(UserAuth.status == 1)
    .where(UserAuth.phone.like('139%'))
)

# 排序
result = await db.execute(
    select(UserAuth)
    .order_by(UserAuth.created_at.desc())
    .limit(10)
)

# 分页
result = await db.execute(
    select(UserAuth)
    .offset(20)
    .limit(10)
)
```

### 聚合查询

```python
# 计数
count = await db.scalar(select(func.count()).select_from(UserAuth))

# 求和
total = await db.scalar(select(func.sum(TradeOrder.total_amount)))

# 分组
result = await db.execute(
    select(UserAuth.status, func.count())
    .group_by(UserAuth.status)
)
```

### 关联查询

```python
# 一对一（使用 selectinload）
result = await db.execute(
    select(UserAuth)
    .options(selectinload(UserAuth.profile))
    .where(UserAuth.id == user_id)
)
user = result.scalar_one_or_none()
print(user.profile.nickname)  # 不会触发额外查询

# 一对多
result = await db.execute(
    select(CarBrand)
    .options(selectinload(CarBrand.series))
)
brands = result.scalars().all()

# 嵌套关联
result = await db.execute(
    select(CarBrand)
    .options(
        selectinload(CarBrand.series)
        .selectinload(CarSeries.models)
    )
)
```

### JOIN 查询

```python
# INNER JOIN
result = await db.execute(
    select(UserAuth, UserProfile)
    .join(UserProfile, UserAuth.id == UserProfile.user_id)
)

# LEFT JOIN
result = await db.execute(
    select(UserAuth, UserProfile)
    .outerjoin(UserProfile, UserAuth.id == UserProfile.user_id)
)
```

---

## ➕ 创建 (INSERT)

```python
# 单条创建
user = UserAuth(
    phone="13800138000",
    email="test@example.com",
    status=1
)
db.add(user)
await db.commit()
await db.refresh(user)  # 获取生成的ID

# 批量创建
users = [
    UserAuth(phone=f"138000{i}", status=1)
    for i in range(100)
]
db.add_all(users)
await db.commit()
```

---

## 📝 更新 (UPDATE)

### 方式1: ORM 更新

```python
result = await db.execute(select(UserAuth).where(UserAuth.id == user_id))
user = result.scalar_one_or_none()

user.phone = "13900000000"
user.status = 1
await db.commit()
```

### 方式2: SQL 更新

```python
# 单条更新
await db.execute(
    update(UserAuth)
    .where(UserAuth.id == user_id)
    .values(phone="13900000000", status=1)
)
await db.commit()

# 批量更新
await db.execute(
    update(UserAuth)
    .where(UserAuth.status == 0)
    .values(status=1)
)
await db.commit()
```

---

## 🗑️ 删除 (DELETE)

### 方式1: ORM 删除

```python
result = await db.execute(select(UserAuth).where(UserAuth.id == user_id))
user = result.scalar_one_or_none()

await db.delete(user)
await db.commit()
```

### 方式2: SQL 删除

```python
# 单条删除
await db.execute(
    delete(UserAuth)
    .where(UserAuth.id == user_id)
)
await db.commit()

# 批量删除
await db.execute(
    delete(UserAuth)
    .where(UserAuth.status == 2)
)
await db.commit()
```

---

## 🔐 事务管理

### 自动事务（推荐）

```python
@router.post("/users")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user = UserAuth(**data.dict())
    db.add(user)
    # 函数结束自动 commit
    # 出错自动 rollback
    return user
```

### 手动事务

```python
async with AsyncSessionLocal() as session:
    try:
        user = UserAuth(phone="13800138000")
        session.add(user)
        
        profile = UserProfile(user_id=user.id, nickname="测试")
        session.add(profile)
        
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
```

### 嵌套事务

```python
async with db.begin_nested():
    # 子事务
    user = UserAuth(phone="13800138000")
    db.add(user)
    await db.flush()  # 获取 ID 但不提交
```

---

## 🎯 FastAPI 路由示例

### 列表查询

```python
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * size
    result = await db.execute(
        select(UserAuth)
        .offset(offset)
        .limit(size)
    )
    return result.scalars().all()
```

### 详情查询

```python
@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserAuth)
        .options(selectinload(UserAuth.profile))
        .where(UserAuth.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    return user
```

### 创建

```python
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user = UserAuth(**data.dict())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
```

### 更新

```python
@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserAuth).where(UserAuth.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    
    for key, value in data.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    await db.commit()
    return user
```

### 删除

```python
@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserAuth).where(UserAuth.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    
    await db.delete(user)
    await db.commit()
```

---

## 🔧 常用工具函数

### 分页查询

```python
async def paginate(
    query,
    page: int,
    size: int,
    db: AsyncSession
):
    """通用分页函数"""
    offset = (page - 1) * size
    
    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # 数据
    result = await db.execute(
        query.offset(offset).limit(size)
    )
    items = result.scalars().all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items
    }
```

### 批量插入

```python
async def bulk_insert(
    model_class,
    data_list: List[dict],
    db: AsyncSession
):
    """批量插入数据"""
    objects = [model_class(**data) for data in data_list]
    db.add_all(objects)
    await db.commit()
    return objects
```

---

## ⚡ 性能优化

### 1. 使用 selectinload 避免 N+1

```python
# ❌ 差：N+1 查询
users = await db.execute(select(UserAuth))
for user in users.scalars():
    profile = user.profile  # 每次都查询数据库

# ✅ 好：一次查询
result = await db.execute(
    select(UserAuth)
    .options(selectinload(UserAuth.profile))
)
```

### 2. 批量操作

```python
# ❌ 差：逐条插入
for data in data_list:
    user = UserAuth(**data)
    db.add(user)
    await db.commit()  # 每次都提交

# ✅ 好：批量插入
users = [UserAuth(**data) for data in data_list]
db.add_all(users)
await db.commit()  # 一次提交
```

### 3. 只查询需要的字段

```python
# ❌ 差：查询所有字段
result = await db.execute(select(UserAuth))

# ✅ 好：只查询需要的字段
result = await db.execute(
    select(UserAuth.id, UserAuth.phone, UserAuth.email)
)
```

---

## 📚 更多资源

- **详细指南**: `MIGRATION_GUIDE.md`
- **检查清单**: `UPGRADE_CHECKLIST.md`
- **转换总结**: `CONVERSION_SUMMARY.md`
- **官方文档**: https://docs.sqlalchemy.org/en/20/

---

**打印此文档作为速查表！** 📄
