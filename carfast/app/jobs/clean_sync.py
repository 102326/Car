import sys
import os
import asyncio
import logging
import time

# 环境补丁
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from sqlalchemy import select, func
from elasticsearch.helpers import async_bulk

from app.core.database import AsyncSessionLocal
from app.core.es import es_client
from app.models.car import CarModel
from app.services.es_service import CarESService
from app.services.car_assembler import fetch_and_assemble_car_docs

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("CleanSync")

BATCH_SIZE = 100  # 每批处理 100 条


async def main():
    logger.info("🚀 [全量同步] 脚本启动...")

    # 1. 确保索引存在
    await CarESService.create_index_if_not_exists()

    start_time = time.time()
    total_synced = 0

    async with AsyncSessionLocal() as session:
        # 2. 获取总数 (用于进度条)
        count_stmt = select(func.count(CarModel.id))
        total_count = (await session.execute(count_stmt)).scalar()
        logger.info(f"📦 数据库共有 {total_count} 辆车，准备同步...")

        # 3. 游标分页查询 (避免一次性加载所有 ID 撑爆内存)
        # 这里为了简单，我们先查出所有 ID，如果 ID 也是百万级，建议用 keyset pagination
        stmt = select(CarModel.id)
        all_ids = (await session.execute(stmt)).scalars().all()

        # 4. 批量处理循环
        client = es_client.get_client()

        for i in range(0, len(all_ids), BATCH_SIZE):
            batch_ids = all_ids[i: i + BATCH_SIZE]

            # A. 批量查库组装 (Batch Fetch)
            docs = await fetch_and_assemble_car_docs(batch_ids)
            if not docs:
                continue

            # B. 构造 ES Bulk Actions
            actions = [
                {
                    "_index": CarESService.INDEX_NAME,
                    "_id": str(d["id"]),
                    "_source": d
                }
                for d in docs
            ]

            # C. 批量写入 ES (Bulk Insert)
            try:
                success, failed = await async_bulk(client, actions, stats_only=True)
                total_synced += success
                print(f"\r   ⏳ 进度: {total_synced}/{total_count} ({(total_synced / total_count) * 100:.1f}%)", end="")
            except Exception as e:
                logger.error(f"\n❌ 批次写入失败: {e}")

    duration = time.time() - start_time
    print()
    logger.info(f"🎉 [完成] 同步 {total_synced} 条数据，耗时 {duration:.2f}秒")
    logger.info(f"⚡ 平均速度: {total_synced / duration:.0f} docs/s")

    # 关闭资源
    await es_client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass