# carfast/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 引入配置
from app.config import settings
# 引入日志配置
from app.core.logging_config import setup_logging
# 引入统一连接管理器
from app.core.connections import connection_manager
# 引入数据库管理（SQLAlchemy - 保持依赖注入）
from app.core.database import init_db, close_db
from app.views.car_view import router as car_router
from app.views.agent_view import router as agent_router

# ==========================================
# 🔧 初始化日志系统（应用启动前）
# ==========================================
setup_logging("INFO")  # 可以通过环境变量配置

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
    FastAPI 生命周期管理器：统一管理所有连接
    """
    print(f"\n [{settings.APP_NAME}] 系统启动序列开始...")
    print("=" * 60)

    # ==========================================
    # 启动阶段：初始化所有连接
    # ==========================================
    
    # 1. 初始化全局连接池（MongoDB, Redis, RabbitMQ, Milvus）
    print("\n[1/2] 初始化全局连接池...")
    await connection_manager.connect_all()
    
    # 将连接管理器挂载到 app.state，供全局访问
    app.state.connections = connection_manager
    
    # 2. 初始化 PostgreSQL（SQLAlchemy - 使用依赖注入）
    print("\n[2/2] 初始化 PostgreSQL...")
    try:
        await init_db()
        log_success("[PostgreSQL] 连接就绪 (使用依赖注入)")
    except Exception as e:
        log_error("[PostgreSQL] 连接失败", e)
        print("    提示: 请检查数据库配置")

    # --- 启动完成 ---
    print("\n" + "=" * 60)
    print("  系统启动完成")
    print("=" * 60)
    print(f"  MongoDB:    {'✅ 已连接' if connection_manager.mongo_db is not None else '❌ 未连接'}")
    print(f"  Redis:      {'✅ 已连接' if connection_manager.redis_client is not None else '❌ 未连接'}")
    print(f"  RabbitMQ:   {'✅ 已连接' if connection_manager.rabbitmq_channel is not None else '⚠️ 未连接（降级运行）'}")
    print(f"  Milvus:     {'✅ 已连接' if connection_manager.milvus_connected else '⚠️ 未连接（可选）'}")
    print(f"  PostgreSQL: ✅ 已就绪（依赖注入）")
    print("=" * 60)
    print("\n💡 提示: 通过 app.state.connections 访问全局连接\n")

    yield  # --- 应用运行中 ---

    # ==========================================
    # 关闭阶段：断开所有连接
    # ==========================================
    print(f"\n [{settings.APP_NAME}] 系统正在关闭...")
    print("=" * 60)
    
    # 1. 断开全局连接
    await connection_manager.disconnect_all()
    
    # 2. 关闭 PostgreSQL
    try:
        await close_db()
        print("PostgreSQL 连接已关闭")
    except Exception as e:
        print(f"PostgreSQL 关闭警告: {e}")
    
    print("=" * 60)
    print(f" [{settings.APP_NAME}] 系统已安全关闭\n")


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

app.include_router(car_router)
app.include_router(agent_router)

@app.get("/")
async def root():
    return {"status": "running", "message": "CarFast API Backend with Smart Car Concierge Agent"}