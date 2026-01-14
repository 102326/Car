# carfast/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 引入配置
from app.config import settings
# 引入 MQ 客户端
from app.core.mq import RabbitMQClient
# 引入数据库管理
from app.database import init_db, close_db


# ==========================================
# 🛠 辅助函数：打印带颜色的日志
# ==========================================
def log_success(msg: str):
    print(f"\033[32m {msg}\033[0m")  # 绿色


def log_error(msg: str, error: Exception = None):
    print(f"\033[31m {msg}\033[0m")  # 红色
    if error:
        print(f"\033[33m   └─ 错误详情: {str(error)}\033[0m")  # 黄色详情


# ==========================================
#  生命周期管理 (核心逻辑)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理器：
    严谨地管理资源连接，拒绝假装成功。
    """
    print(f"\n [{settings.APP_NAME}] 系统启动序列开始...")

    has_critical_error = False

    # 1. 尝试连接 RabbitMQ
    # ------------------------------------------------
    try:
        print("   ├─ 正在连接消息队列 (RabbitMQ)...")
        await RabbitMQClient.connect()
        # 双重检查：确保连接对象真的存在且开启
        if RabbitMQClient.connection and not RabbitMQClient.connection.is_closed:
            log_success("[消息队列] RabbitMQ 连接就绪")
        else:
            raise ConnectionError("连接函数未报错，但连接对象未建立 (逻辑异常)")

    except Exception as e:
        has_critical_error = True
        log_error("[消息队列] 连接失败！", e)
        print("    提示: 请检查 Docker 是否开启? 端口 5672 是否映射?")

    # 2. 尝试连接 数据库 (PostgreSQL with SQLAlchemy)
    # ------------------------------------------------
    try:
        print("   ├─ 正在连接数据库 (PostgreSQL with SQLAlchemy)...")
        # 初始化数据库表（开发环境，生产环境建议用 Alembic）
        await init_db()
        log_success("[数据库] PostgreSQL 连接就绪 (SQLAlchemy)")

    except Exception as e:
        has_critical_error = True
        log_error("[数据库] 连接失败！", e)
        print("    提示: 请检查 Docker 是否开启? 端口 5432 是否映射?")

    # --- 启动结果汇总 ---
    if has_critical_error:
        print("\n\033[1;31m  严重警告: 部分核心服务启动失败，系统可能无法正常工作 \033[0m\n")
    else:
        print("\n\033[1;32m  系统启动成功，等待请求中... \033[0m\n")

    yield  # --- 应用运行中 ---

    # 3. 关闭资源
    # ------------------------------------------------
    print(f"\n [{settings.APP_NAME}] 系统正在关闭...")

    try:
        await RabbitMQClient.close()
        print("   └─ [消息队列] 连接已断开")
    except:
        pass

    try:
        await close_db()
        print("   └─ [数据库] 连接已断开")
    except:
        pass


# ==========================================
# ⚡ 应用初始化
# ==========================================
app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

# 配置跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "running", "message": "CarFast API Backend"}