# carfast/app/core/celery_app.py
import sys
from celery import Celery
from app.config import settings

# 1. Windows 兼容补丁
if sys.platform == "win32":
    try:
        import eventlet

        eventlet.monkey_patch()
    except ImportError:
        pass

# 2. 初始化 App
celery_app = Celery(
    "pylab_worker",  # 建议改个更有辨识度的名字
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 3. 配置升级 (企业级配置)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    broker_heartbeat=10,

    # === 新增的高并发优化配置 ===
    # 防止一个 Worker 领太多任务导致其他 Worker 闲置
    worker_prefetch_multiplier=1,
    # 任务执行完再确认 ACK，防止 Worker 崩溃导致任务丢失
    task_acks_late=True,
    # 单个任务超时限制 (防止死循环占用资源)
    task_time_limit=60,
)

# 4. 自动发现任务
# 这一步非常重要，指向我们下一步要创建的文件
celery_app.autodiscover_tasks(["app.tasks.sync_tasks","app.tasks.auth_tasks"])