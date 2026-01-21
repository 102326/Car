import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiokafka import AIOKafkaConsumer

from app.consumers.cdc_sync import SmartBuffer


@pytest.fixture
def mock_consumer():
    consumer = AsyncMock(spec=AIOKafkaConsumer)
    consumer.assignment.return_value = set()
    return consumer


@pytest.fixture
def smart_buffer(mock_consumer):
    # max_events=10, hard_limit=20
    return SmartBuffer(mock_consumer, max_events=10, hard_limit=20, max_wait=60.0)


@pytest.mark.asyncio
async def test_buffer_accumulate(smart_buffer):
    """测试 1: 缓冲区是否能正常积攒事件，不到阈值不 Flush"""
    with patch.object(smart_buffer, 'flush', new_callable=AsyncMock) as mock_flush:
        for i in range(5):
            await smart_buffer.add_event('car_model', i)
        mock_flush.assert_not_called()
        assert len(smart_buffer.event_buffer) == 5


@pytest.mark.asyncio
async def test_buffer_trigger_flush(smart_buffer):
    """测试 2: 达到 max_events 是否触发 Flush"""
    with patch.object(smart_buffer, 'flush', new_callable=AsyncMock) as mock_flush:
        for i in range(10):
            await smart_buffer.add_event('car_model', i)
        mock_flush.assert_called_once()


@pytest.mark.asyncio
async def test_backpressure_pause(smart_buffer, mock_consumer):
    """测试 3: 达到 hard_limit 是否触发流控 (Pause)"""

    # ✅ [修复] Mock 掉 flush，防止它清空缓冲区，确保能达到 hard_limit (20)
    with patch.object(smart_buffer, 'flush', new_callable=AsyncMock) as mock_flush:
        for i in range(20):
            await smart_buffer.add_event('car_model', i)

        # 断言: 消费者应该被暂停
        mock_consumer.pause.assert_called_once()
        assert smart_buffer.paused is True


@pytest.mark.asyncio
async def test_backpressure_resume(smart_buffer, mock_consumer):
    """测试 4: Flush 后是否恢复消费 (Resume)"""
    smart_buffer.paused = True
    smart_buffer.event_buffer = {('car_model', i) for i in range(20)}

    # Mock 内部依赖，避免真实数据库连接
    with patch('app.consumers.cdc_sync.fetch_and_assemble_car_docs', new_callable=AsyncMock) as mock_fetch, \
            patch('app.services.es_service.CarESService.bulk_sync_cars', new_callable=AsyncMock) as mock_es_sync, \
            patch.object(smart_buffer, '_batch_resolve_events', new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = set()
        await smart_buffer.flush()

        mock_consumer.resume.assert_called_once()
        assert smart_buffer.paused is False
        assert len(smart_buffer.event_buffer) == 0


@pytest.mark.asyncio
async def test_retry_logic(smart_buffer):
    """测试 5: ES 写入失败后，ID 是否进入重试队列"""
    smart_buffer.event_buffer.add(('car_model', 101))

    with patch('app.consumers.cdc_sync.fetch_and_assemble_car_docs', new_callable=AsyncMock) as mock_fetch, \
            patch('app.services.es_service.CarESService.bulk_sync_cars', new_callable=AsyncMock) as mock_es_sync, \
            patch.object(smart_buffer, '_batch_resolve_events', new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = {101}
        mock_fetch.return_value = [{"id": 101, "name": "Test Car"}]
        # ES 返回失败 ID
        mock_es_sync.return_value = [101]

        await smart_buffer.flush()

        assert 101 in smart_buffer.retry_buffer
        assert smart_buffer.retry_buffer[101] == 1


@pytest.mark.asyncio
async def test_dlq_drop(smart_buffer):
    """测试 6: 超过最大重试次数是否丢弃 (DLQ)"""
    # 1. 模拟已经重试 3 次
    smart_buffer.retry_buffer[101] = 3

    # 2. 再次重试
    await smart_buffer.add_retry_ids([101])

    # 3. 断言: 应该被删除
    assert 101 not in smart_buffer.retry_buffer