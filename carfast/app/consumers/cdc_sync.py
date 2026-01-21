import asyncio
import json
import logging
import time
from typing import Set, Tuple, List, Dict

from aiokafka import AIOKafkaConsumer, TopicPartition
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.car import CarModel, CarSeries
from app.services.car_assembler import fetch_and_assemble_car_docs
from app.services.es_service import CarESService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CDC_Sync")


# ==========================================
# 🛡️ 智能缓冲区 (Pro Max)
# ==========================================
class SmartBuffer:
    def __init__(self, consumer: AIOKafkaConsumer, max_events=2000, hard_limit=5000, max_wait=1.0):
        self.consumer = consumer
        self.max_events = max_events  # 触发 Flush 的软阈值
        self.hard_limit = hard_limit  # 触发 Pause 的硬阈值
        self.max_wait = max_wait

        self.event_buffer: Set[Tuple[str, int]] = set()
        self.retry_buffer: Dict[int, int] = {}
        self.MAX_RETRIES = 3

        self.last_flush_time = time.time()
        self._lock = asyncio.Lock()
        self.paused = False

    async def add_event(self, table: str, row_id: int):
        async with self._lock:
            self.event_buffer.add((table, row_id))
            current_size = len(self.event_buffer) + len(self.retry_buffer)

        # 1. 🛑 流控 (Backpressure)
        if current_size >= self.hard_limit and not self.paused:
            logger.warning(f"🛑 Buffer 爆满 ({current_size})，暂停消费 Kafka...")
            self.consumer.pause(*self.consumer.assignment())
            self.paused = True

        # 2. 触发 Flush
        if current_size >= self.max_events:
            await self.flush()

    async def add_retry_ids(self, ids: List[int]):
        """处理失败重试 & 死信队列 (DLQ)"""
        async with self._lock:
            for i in ids:
                count = self.retry_buffer.get(i, 0) + 1
                if count <= self.MAX_RETRIES:
                    self.retry_buffer[i] = count
                else:
                    # 💀 死信处理 (DLQ)
                    logger.error(f"💀 [DLQ] ID {i} 重试 {count} 次仍失败，彻底丢弃！")
                    # ✅ [修复] 显式从重试队列中移除，防止死循环
                    if i in self.retry_buffer:
                        del self.retry_buffer[i]

    async def flush(self):
        """核心同步逻辑"""
        async with self._lock:
            if not self.event_buffer and not self.retry_buffer:
                return

            # 提取快照
            events = list(self.event_buffer)
            # 暂存旧的 retry counts，用于后续恢复
            old_retry_counts = self.retry_buffer.copy()

            self.event_buffer.clear()
            self.retry_buffer.clear()

            self.last_flush_time = time.time()

            # ▶️ 恢复消费
            if self.paused:
                logger.info("▶️ Buffer 压力释放，恢复消费 Kafka...")
                self.consumer.resume(*self.consumer.assignment())
                self.paused = False

        # 1. 解析所有受影响的 Car ID
        impacted_ids = set(old_retry_counts.keys())
        if events:
            resolved = await self._batch_resolve_events(events)
            impacted_ids.update(resolved)

        if not impacted_ids:
            await self._commit_offset()
            return

        logger.info(f"⚡ [Flush] 处理 {len(impacted_ids)} 个 Car ID")

        # 2. 批量处理
        all_ids = list(impacted_ids)
        chunk_size = 500

        for i in range(0, len(all_ids), chunk_size):
            batch_ids = all_ids[i: i + chunk_size]

            found_docs = await fetch_and_assemble_car_docs(batch_ids)
            found_ids = {d['id'] for d in found_docs}
            missing_ids = [bid for bid in batch_ids if bid not in found_ids]

            failed_upsert = []
            if found_docs:
                failed_upsert = await CarESService.bulk_sync_cars(found_docs)

            failed_delete = []
            if missing_ids:
                failed_delete = await CarESService.bulk_delete_cars(missing_ids)

            # 恢复重试计数
            current_failed = set(failed_upsert + failed_delete)
            if current_failed:
                async with self._lock:
                    for fid in current_failed:
                        # 恢复之前的计数
                        if fid in old_retry_counts:
                            self.retry_buffer[fid] = old_retry_counts[fid]

                # 再次加入重试逻辑（这里会 +1 并判断是否 DLQ）
                await self.add_retry_ids(list(current_failed))

        await self._commit_offset()

    async def _batch_resolve_events(self, events: List[Tuple[str, int]]) -> Set[int]:
        final_ids = set()
        model_ids = [eid for t, eid in events if t == 'car_model']
        series_ids = [eid for t, eid in events if t == 'car_series']
        brand_ids = [eid for t, eid in events if t == 'car_brand']

        final_ids.update(model_ids)

        async with AsyncSessionLocal() as session:
            chunk_size = 500
            for i in range(0, len(series_ids), chunk_size):
                chunk = series_ids[i:i + chunk_size]
                if not chunk: continue
                stmt = select(CarModel.id).where(CarModel.series_id.in_(chunk))
                res = await session.execute(stmt)
                final_ids.update(res.scalars().all())

            for i in range(0, len(brand_ids), chunk_size):
                chunk = brand_ids[i:i + chunk_size]
                if not chunk: continue
                stmt = (
                    select(CarModel.id)
                    .join(CarSeries, CarModel.series_id == CarSeries.id)
                    .where(CarSeries.brand_id.in_(chunk))
                )
                res = await session.execute(stmt)
                final_ids.update(res.scalars().all())

        return final_ids

    async def _commit_offset(self):
        try:
            await self.consumer.commit()
        except Exception as e:
            logger.error(f"❌ Offset Commit Failed: {e}")

    async def auto_flush_loop(self):
        while True:
            await asyncio.sleep(0.5)
            async with self._lock:
                should_flush = (
                        (self.event_buffer or self.retry_buffer) and
                        (time.time() - self.last_flush_time > self.max_wait)
                )
            if should_flush:
                await self.flush()


async def consume():
    await CarESService.create_index_if_not_exists()

    consumer = AIOKafkaConsumer(
        'cdc.car.car_model',
        'cdc.car.car_series',
        'cdc.car.car_brand',
        bootstrap_servers='localhost:9092',
        group_id='es_sync_group_max',
        enable_auto_commit=False,
        auto_offset_reset='latest'
    )

    await consumer.start()
    logger.info("🚀 [Pro Max] CDC Consumer Started")

    buffer = SmartBuffer(consumer, max_events=2000, hard_limit=5000, max_wait=1.0)
    asyncio.create_task(buffer.auto_flush_loop())

    try:
        async for msg in consumer:
            if not msg.value: continue
            try:
                data = json.loads(msg.value)
                payload = data.get('payload')
                if not payload: continue

                op = payload['op']
                row = payload.get('before') if op == 'd' else payload.get('after')
                if not row: continue

                table = msg.topic.split('.')[-1]
                row_id = row['id']
                await buffer.add_event(table, row_id)

            except Exception as e:
                logger.error(f"❌ Parse Error: {e}")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        pass