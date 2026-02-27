# carfast/main.py
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 🚀 解决 HuggingFace 国内网络阻断导致启动卡顿 20 秒的问题
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"  # 方案一：使用国内稳定镜像源
# os.environ["HF_HUB_OFFLINE"] = "1"                 # 方案二：如果模型已下载，强行要求离线运行（可选）

# ==========================================
# 🌟 新增：配置全局标准日志 (极其重要)
# 只有配置了这个，你才能在终端看到 agent 里的 logger.info
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# 屏蔽掉一些第三方库太吵的底层日志
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("elastic_transport").setLevel(logging.WARNING)
logging.getLogger("pika").setLevel(logging.WARNING)

from app.core.es import es_client
# 引入配置
from app.config import settings
from app.api.v1 import chat
from app.api.v1 import agent
# 引入 MQ 客户端
from app.core.mq import RabbitMQClient
# 引入数据库管理
from app.core.database import init_db, close_db
from app.api.v1 import search, auth, car, behavior


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
    print(f"\n [{settings.APP_NAME}] 系统启动序列开始 (启用 5 秒超时控制)...")

    # 服务状态记录
    services_status = {
        "rabbitmq": False,
        "database": False,
        "elasticsearch": False
    }

    # 全局超时时间设置
    TIMEOUT_SEC = 5.0

    # 1. 尝试连接 RabbitMQ（非关键服务，失败可降级）
    # ------------------------------------------------
    try:
        print("   ├─ 正在连接消息队列 (RabbitMQ)...")
        # 🌟 修改：加入 asyncio.wait_for 强制超时
        await asyncio.wait_for(RabbitMQClient.connect(), timeout=TIMEOUT_SEC)

        # 双重检查：确保连接对象真的存在且开启
        if RabbitMQClient.connection and not RabbitMQClient.connection.is_closed:
            log_success("[消息队列] RabbitMQ 连接就绪")
            services_status["rabbitmq"] = True
        else:
            raise ConnectionError("连接函数未报错，但连接对象未建立 (逻辑异常)")

    except asyncio.TimeoutError:
        log_error(f"[消息队列] 连接超时（超过 {TIMEOUT_SEC} 秒，将降级运行）")
        print("    提示: 消息队列功能将不可用，但不影响基础API功能")
    except Exception as e:
        log_error("[消息队列] 连接失败（非关键服务，将降级运行）", e)
        print("    提示: 消息队列功能将不可用，但不影响基础API功能")
        print("    如需启用: docker run -d -p 5672:5672 rabbitmq:3-management")

    # 2. 尝试连接 数据库 (PostgreSQL with SQLAlchemy)
    # ------------------------------------------------
    try:
        print("   ├─ 正在连接数据库 (PostgreSQL with SQLAlchemy)...")
        # 🌟 修改：加入 asyncio.wait_for 强制超时
        await asyncio.wait_for(init_db(), timeout=TIMEOUT_SEC)
        log_success("[数据库] PostgreSQL 连接就绪 (SQLAlchemy)")
        services_status["database"] = True

    except asyncio.TimeoutError:
        log_error(f"[数据库] 连接超时（超过 {TIMEOUT_SEC} 秒，关键服务！）")
        print("    提示: 请确认数据库服务已启动且网络通畅")
    except Exception as e:
        log_error("[数据库] 连接失败（关键服务）", e)
        print("    提示: 请检查数据库配置:")
        print(f"    - 当前配置: {settings.DB_URL.split('@')[1] if '@' in settings.DB_URL else 'unknown'}")
        print("    - 请确认数据库服务已启动且配置正确")
        print("    - 本地: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=123456 postgres:15")
        print("    - 或修改 .env 使用远程数据库")

    # === 初始化 ES ===
    try:
        print("   ├─ 正在连接搜索引擎 (Elasticsearch)...")

        # 🌟 修改：加入 asyncio.wait_for 强制超时
        async def _init_es():
            info = await es_client.get_client().info()
            return info["version"]["number"]

        version = await asyncio.wait_for(_init_es(), timeout=TIMEOUT_SEC)
        log_success(f"[搜索引擎] Elasticsearch 连接就绪 (v{version})")
        services_status["elasticsearch"] = True
    except asyncio.TimeoutError:
        log_error(f"[搜索引擎] 连接超时（超过 {TIMEOUT_SEC} 秒，搜索功能将不可用）")
    except Exception as e:
        log_error("[搜索引擎] 连接失败（搜索功能将不可用）", e)

    # --- 启动结果汇总 ---
    print("\n" + "=" * 60)
    print("  服务状态汇总")
    print("=" * 60)
    print(
        f"  {'✅' if services_status['database'] else '❌'} 数据库 (PostgreSQL): {'已连接' if services_status['database'] else '未连接'}")
    print(
        f"  {'✅' if services_status['rabbitmq'] else '⚠️'} 消息队列 (RabbitMQ): {'已连接' if services_status['rabbitmq'] else '未连接（降级运行）'}")
    print(
        f"  {'✅' if services_status['elasticsearch'] else '⚠️'} 搜索引擎 (Elasticsearch): {'已连接' if services_status['elasticsearch'] else '未连接'}")
    print("=" * 60)

    if not services_status["database"]:
        print("\033[1;31m  ⚠️  数据库未连接，大部分 API 将无法使用！\033[0m")
        print("  请修复数据库连接后重启应用")
    elif not services_status["rabbitmq"] or not services_status["elasticsearch"]:
        print("\033[1;33m  ⚠️  部分非核心服务未连接，系统将降级运行\033[0m")
    else:
        print("\033[1;32m  🎉 所有服务已就绪，系统运行正常！\033[0m")

    print("=" * 60)
    print()

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
    try:
        await es_client.close()
        print("   └─ [搜索引擎] 连接已断开")
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

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(car.router, prefix="/api/v1/cars", tags=["Car"])
app.include_router(behavior.router, prefix="/api/v1/user", tags=["User Behavior"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["AI Chat"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])


@app.get("/")
async def root():
    return {"status": "running", "message": "CarFast API Backend"}