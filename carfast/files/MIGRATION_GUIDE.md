# 🔄 数据库迁移从 Tortoise ORM 到 SQLAlchemy 完全指南

## 📋 转换概览

本项目已从 **Tortoise ORM** 完全迁移至 **SQLAlchemy 2.0**（异步版本）。

### ✅ 已完成的修改

| 文件 | 修改内容 |
|------|---------|
| `app/database.py` | ✨ **新增** - SQLAlchemy 引擎和会话管理 |
| `main.py` | 🔄 替换 Tortoise 初始化为 SQLAlchemy |
| `app/utils/deps.py` | 🔄 依赖注入改用 SQLAlchemy 查询 |
| `requirements.txt` | 🔄 移除 `tortoise-orm`，添加 `sqlalchemy[asyncio]` |
| `app/models/__init__.py` | ✨ **新增** - 统一导出所有模型 |
| `alembic.ini` | ✨ **新增** - Alembic 迁移配置 |
| `alembic/env.py` | ✨ **新增** - Alembic 环境配置 |

---

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
# 安装更新的依赖包
pip install -r requirements.txt

# 或者直接安装关键包
pip install sqlalchemy[asyncio]==2.0.40 alembic==1.15.2 asyncpg==0.31.0
```

### 2️⃣ 初始化 Alembic

```bash
# 已经创建好了配置文件，直接生成初始迁移
alembic revision --autogenerate -m "initial migration"
```

### 3️⃣ 执行迁移

```bash
# 升级到最新版本
alembic upgrade head

# 查看迁移历史
alembic history

# 回退一个版本
alembic downgrade -1
```

### 4️⃣ 启动应用

```bash
# 启动 FastAPI 服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📚 核心代码变化对比

### ⚙️ 数据库初始化

#### ❌ 之前 (Tortoise ORM)

```python
from tortoise import Tortoise

await Tortoise.init(
    db_url=settings.DB_URL,
    modules={"models": ["app.models"]},
    timezone="Asia/Shanghai"
)
await Tortoise.generate_schemas()
```

#### ✅ 现在 (SQLAlchemy 2.0)

```python
from app.core.database import init_db, close_db

# 启动时
await init_db()

# 关闭时
await close_db()
```

---

### 🔍 数据库查询

#### ❌ 之前 (Tortoise ORM)

```python
# 查询单个用户
user = await User.get(id=user_id)
user = await User.get_or_none(id=user_id)

# 查询列表
users = await User.all()
users = await User.filter(status=1).all()

# 关联查询
user = await User.get(id=1).prefetch_related("profile")
```

#### ✅ 现在 (SQLAlchemy 2.0)

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 查询单个用户
result = await db.execute(select(UserAuth).where(UserAuth.id == user_id))
user = result.scalar_one_or_none()

# 查询列表
result = await db.execute(select(UserAuth))
users = result.scalars().all()

# 带条件查询
result = await db.execute(select(UserAuth).where(UserAuth.status == 1))
users = result.scalars().all()

# 关联查询（使用 joinedload）
from sqlalchemy.orm import selectinload
result = await db.execute(
    select(UserAuth)
    .options(selectinload(UserAuth.profile))
    .where(UserAuth.id == user_id)
)
user = result.scalar_one_or_none()
```

---

### 💾 增删改操作

#### ❌ 之前 (Tortoise ORM)

```python
# 创建
user = await User.create(phone="13800138000", email="test@example.com")

# 更新
await user.update_from_dict({"nickname": "新昵称"}).save()

# 删除
await user.delete()

# 批量更新
await User.filter(status=0).update(status=1)
```

#### ✅ 现在 (SQLAlchemy 2.0)

```python
from sqlalchemy import update, delete

# 创建
user = UserAuth(phone="13800138000", email="test@example.com")
db.add(user)
await db.commit()
await db.refresh(user)  # 获取生成的 ID

# 更新（方式1：对象更新）
user.nickname = "新昵称"
await db.commit()

# 更新（方式2：SQL 更新）
await db.execute(
    update(UserAuth)
    .where(UserAuth.id == user_id)
    .values(nickname="新昵称")
)
await db.commit()

# 删除
await db.delete(user)
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

### 🎯 依赖注入

#### ❌ 之前 (Tortoise ORM)

```python
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await User.get(id=user_id)
    return user
```

#### ✅ 现在 (SQLAlchemy 2.0)

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db


@router.get("/users/{user_id}")
async def get_user(
        user_id: int,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserAuth).where(UserAuth.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
```

---

## 🛠 常用 Alembic 命令

```bash
# 📝 创建迁移脚本（自动检测模型变化）
alembic revision --autogenerate -m "add user table"

# 📝 手动创建空迁移脚本
alembic revision -m "custom migration"

# ⬆️ 升级到最新版本
alembic upgrade head

# ⬆️ 升级到指定版本
alembic upgrade <revision_id>

# ⬇️ 回退一个版本
alembic downgrade -1

# ⬇️ 回退到指定版本
alembic downgrade <revision_id>

# 📜 查看迁移历史
alembic history

# 🔍 查看当前版本
alembic current

# 📄 生成 SQL 脚本（不执行）
alembic upgrade head --sql > migration.sql
```

---

## ⚠️ 注意事项

### 1. 异步上下文

SQLAlchemy 2.0 使用异步驱动，所有数据库操作必须使用 `await`：

```python
# ✅ 正确
result = await db.execute(select(User))
users = result.scalars().all()

# ❌ 错误
result = db.execute(select(User))  # 缺少 await
```

### 2. 会话管理

使用 `Depends(get_db)` 自动管理会话生命周期：

```python
@router.post("/users")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)  # 自动提交/回滚
):
    user = UserAuth(**user_data.dict())
    db.add(user)
    # 函数结束时自动 commit，出错时自动 rollback
    return user
```

### 3. 关联查询性能

使用 `selectinload` 或 `joinedload` 避免 N+1 查询问题：

```python
from sqlalchemy.orm import selectinload

# ✅ 高效：一次查询加载关联
result = await db.execute(
    select(UserAuth)
    .options(selectinload(UserAuth.profile))
)

# ❌ 低效：每个用户触发一次额外查询
users = result.scalars().all()
for user in users:
    profile = user.profile  # 如果没有 selectinload，会触发新查询
```

---

## 🎓 学习资源

- [SQLAlchemy 2.0 官方文档](https://docs.sqlalchemy.org/en/20/)
- [SQLAlchemy 异步教程](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic 迁移文档](https://alembic.sqlalchemy.org/en/latest/)

---

## ✨ 完成！

现在你的项目已经完全使用 **SQLAlchemy 2.0**，享受更强大的查询能力和更好的类型提示吧！ 🎉
