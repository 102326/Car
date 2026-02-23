# app/utils/decorators.py
import time
import logging
from functools import wraps

# 初始化 logger
logger = logging.getLogger(__name__)


def async_time_it(func):
    """
    异步函数耗时统计装饰器
    用于监控 LangGraph 各个节点的执行性能
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 使用 perf_counter 提供生产级的高精度耗时统计
        start_time = time.perf_counter()

        # 执行原异步函数
        result = await func(*args, **kwargs)

        # 计算耗时并使用标准的 logger.info 打印
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        logger.info(f"[性能监控] 节点/函数 '{func.__name__}' 耗时: {elapsed_ms:.2f} ms")

        return result

    return wrapper