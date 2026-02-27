# carfast/main.py
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# 1. 导入刚刚写的 Trace ID 工具
from app.utils.trace import generate_trace_id, get_trace_id

# 🚀 解决 HuggingFace 国内网络阻断导致启动卡顿 20 秒的问题
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


# ==========================================
# 🌟 企业级 APM 改造：自定义日志 Formatter
# 让每一行日志自动带上当前的 Trace ID
# ==========================================
class TraceFormatter(logging.Formatter):
    def format(self, record):
        record.trace_id = get_trace_id()
        return super().format(record)


# 清除默认的 handlers
logging.root.handlers = []

# 设置自定义的 Handler 和 Formatter
console_handler = logging.StreamHandler()
# 日志格式中加入了 [%(trace_id)s]
formatter = TraceFormatter("%(asctime)s | %(levelname)-8s | [%(trace_id)s] | %(name)s | %(message)s",
                           "%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(formatter)
logging.root.addHandler(console_handler)
logging.root.setLevel(logging.INFO)

# 屏蔽掉一些第三方库太吵的底层日志
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("elastic_transport").setLevel(logging.WARNING)
logging.getLogger("pika").setLevel(logging.WARNING)

from app.core.es import es_client
from app.config import settings
from app.api.v1 import chat, agent, search, auth, car, behavior
from app.core.mq import RabbitMQClient
from app.core.database import init_db, close_db


# ==========================================
# 🛠 辅助函数：打印带颜色的日志
# ==========================================
def log_success(msg: str):
    print(f"\033[32m {msg}\033[0m")


def log_error(msg: str, error: Exception = None):
    print(f"\033[31m {msg}\033[0m")
    if error:
        print(f"\033[33m   └─ 错误详情: {str(error)}\033[0m")


# ==========================================
#  生命周期管理 (核心逻辑)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"\n [{settings.APP_NAME}] 系统启动序列开始 (启用 5 秒超时控制)...")
    services_status = {"rabbitmq": False, "database": False, "elasticsearch": False}
    TIMEOUT_SEC = 5.0

    try:
        print("   ├─ 正在连接消息队列 (RabbitMQ)...")
        await asyncio.wait_for(RabbitMQClient.connect(), timeout=TIMEOUT_SEC)
        if RabbitMQClient.connection and not RabbitMQClient.connection.is_closed:
            log_success("[消息队列] RabbitMQ 连接就绪")
            services_status["rabbitmq"] = True
    except Exception as e:
        log_error("[消息队列] 连接异常，将降级运行")

    try:
        print("   ├─ 正在连接数据库 (PostgreSQL with SQLAlchemy)...")
        await asyncio.wait_for(init_db(), timeout=TIMEOUT_SEC)
        log_success("[数据库] PostgreSQL 连接就绪")
        services_status["database"] = True
    except Exception as e:
        log_error("[数据库] 连接失败（关键服务）")

    try:
        print("   ├─ 正在连接搜索引擎 (Elasticsearch)...")

        async def _init_es():
            info = await es_client.get_client().info()
            return info["version"]["number"]

        version = await asyncio.wait_for(_init_es(), timeout=TIMEOUT_SEC)
        log_success(f"[搜索引擎] Elasticsearch 连接就绪 (v{version})")
        services_status["elasticsearch"] = True
    except Exception as e:
        log_error("[搜索引擎] 连接失败（搜索功能将不可用）")

    yield  # --- 应用运行中 ---

    print(f"\n [{settings.APP_NAME}] 系统正在关闭...")
    try:
        await RabbitMQClient.close()
    except:
        pass
    try:
        await close_db()
    except:
        pass
    try:
        await es_client.close()
    except:
        pass


# ==========================================
# ⚡ 应用初始化
# ==========================================
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)


# ==========================================
# 🌟 企业级 APM 改造：全局 TraceID 中间件
# 拦截所有请求，生成唯一 ID，并塞入 Header 响应
# ==========================================
@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    # 生成 8 位短 Trace ID 并注入异步上下文
    trace_id = generate_trace_id()

    # 将请求交给后端路由处理
    response = await call_next(request)

    # 响应头上附带这个 ID，方便前端拿去报错截图或客诉排查
    response.headers["X-Trace-ID"] = trace_id
    return response


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