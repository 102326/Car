import os
from celery import Celery, Task
from celery.signals import worker_ready

# 读取配置 (注意: Celery 是独立进程, 必须确保能读到环境变量)
# 建议在 main.py 或 worker 入口加载 .env, 或者依赖 docker 的 env
broker_url = os.getenv("CELERY_BROKER_URL", "amqp://user:password@localhost:5672/")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")


class RobustTask(Task):
    """
    🛡️ 工程化增强：健壮任务基类
    1. 自动重试：网络抖动自动重发
    2. 统一日志：标准化的 Log 格式
    3. 异常捕获：防止 Worker 崩溃
    """
    autoretry_for = (Exception,)  # 所有异常都重试 (可按需缩小范围)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True  # 指数退避 (1s, 2s, 4s...)
    retry_backoff_max = 60  # 最大等待 60s
    retry_jitter = True  # 加入随机抖动，防止惊群效应
    acks_late = True  # 关键：任务执行成功后才确认 (防止执行中 crash 导致丢任务)


# 初始化
celery_app = Celery(
    "carfast_worker",
    broker=broker_url,
    backend=result_backend,
    task_cls=RobustTask  # 👈 全局应用增强基类
)

# === ⚙️ 工程化配置 ===
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,

    # --- 🚦 队列路由 (P1/P2 分流) ---
    task_default_queue="default",
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "priority_high": {"exchange": "priority", "routing_key": "high"},  # P1: 验证码、支付通知
        "priority_low": {"exchange": "priority", "routing_key": "low"},  # P2: 报表、清理
    },
    task_routes={
        # 显式路由：认证类任务走高优队列
        "app.tasks.auth_tasks.*": {"queue": "priority_high"},
        # 其他默认走 default
        "*": {"queue": "default"},
    },

    # --- ⚡ 性能优化 (针对副作用任务) ---
    worker_prefetch_multiplier=1,  # 防止 Worker 贪多嚼不烂
    task_time_limit=30,  # 硬超时：30秒没跑完直接 Kill
    task_soft_time_limit=25,  # 软超时：25秒抛异常给机会处理
)

# 自动发现
celery_app.autodiscover_tasks(["app.tasks.auth_tasks"])