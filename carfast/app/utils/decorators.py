# carfast/app/utils/decorators.py
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def async_time_it(func):
    """
    异步函数耗时统计装饰器。
    用于精准监控 LangGraph 每个节点的执行时间。
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()

        # 执行原函数
        result = await func(*args, **kwargs)

        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000

        logger.info(f"[性能监控] 节点/函数 '{func.__name__}' 耗时: {elapsed_ms:.2f} ms")

        return result

    return wrapper