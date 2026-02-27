# carfast/app/utils/trace.py
import contextvars
import uuid

# 定义一个全局的上下文变量，默认值为 "-"
request_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")

def generate_trace_id() -> str:
    """生成一个 8 位的短 UUID 作为 Trace ID，并注入当前上下文"""
    trace_id = uuid.uuid4().hex[:8]
    request_trace_id.set(trace_id)
    return trace_id

def get_trace_id() -> str:
    """获取当前上下文的 Trace ID"""
    return request_trace_id.get()