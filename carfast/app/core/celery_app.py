# app/core/celery_app.py
import os
import sys
from celery import Celery
from app.config import settings

# 1. Windows 兼容补丁 (如果你在 WSL 里跑，这一步其实不会触发，因为 sys.platform 是 linux)
if sys.platform == "win32":
    try:
        import eventlet
        eventlet.monkey_patch()
    except ImportError:
        pass

# 2. 初始化 App
celery_app = Celery(
    "new_project_worker", # 改个名字
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 3. 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    broker_heartbeat=10,
)

# 4. 自动发现任务 (记得修改你的任务路径)
celery_app.autodiscover_tasks(["app.tasks.ai_tasks"]) # 假设新任务在这里