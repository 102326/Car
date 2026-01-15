import sys
import os
import asyncio
import logging
from celery import Celery
from sqlalchemy import select

# ==========================================
# 0. 环境补丁
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# 仅引入必要的数据库模型
from app.core.database import AsyncSessionLocal
from app.models.car import CarModel

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CleanSync")

# ==========================================
# ⚡️ 1. 显式配置区 (请在此处填入你的配置)
# ==========================================
# 注意：RabbitMQ 的 "/" Vhost 必须转义为 "%2f"
# 格式：amqp://user:password@ip:port/vhost
BROKER_URL = "amqp://user:password@127.0.0.1:5672/%2f"

logger.info("🔧 初始化临时 Celery 客户端...")
logger.info(f"   目标 Broker: {BROKER_URL}")

# 创建一个临时的 Celery App，只用来发任务
# 不依赖 app.core.celery_app，隔离环境干扰
temp_app = Celery("temp_sender", broker=BROKER_URL)
temp_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    broker_connection_retry_on_startup=True
)


async def main():
    logger.info("🚀 [CleanSync] 全量同步脚本启动")

    # 1. 连接测试 (先发一个 ping 看看通不通)
    try:
        with temp_app.connection_for_write() as conn:
            conn.connect()
            logger.info("✅ [连接成功] RabbitMQ 连接畅通，权限验证通过！")
    except Exception as e:
        logger.error(f"❌ [连接失败] 无法连接 RabbitMQ，请检查密码或权限: {e}")
        return

    # 2. 查库
    logger.info("🔍 正在扫描数据库...")
    async with AsyncSessionLocal() as session:
        stmt = select(CarModel.id)
        result = await session.execute(stmt)
        car_ids = result.scalars().all()

        total = len(car_ids)
        if total == 0:
            logger.warning("⚠️ 数据库为空，没有任务可发。")
            return

        logger.info(f"📦 发现 {total} 辆车，准备下发任务...")

        # 3. 批量发送
        # 使用 send_task 而不是 task.delay，解耦代码引用
        success_count = 0
        for pid in car_ids:
            try:
                temp_app.send_task(
                    "sync_car_to_es",  # 任务名必须和 sync_tasks.py 里的一致
                    args=[pid, "update"],
                    queue="celery"  # 默认队列名
                )
                success_count += 1
                if success_count % 100 == 0:
                    print(f"   >> 已发送 {success_count}/{total} ...")
            except Exception as e:
                logger.error(f"❌ 发送 ID={pid} 失败: {e}")

        logger.info(f"🎉 [完成] 成功下发 {success_count} 个同步任务！")
        logger.info("👉 请检查 Celery Worker 终端查看消费情况。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"💥 脚本崩溃: {e}")