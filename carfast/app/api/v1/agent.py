"""
Agent API Endpoints for CarFast.
This module exposes the LangGraph agent via FastAPI REST endpoints.
"""

import logging
import time
import hashlib
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse  # 🌟 新增：引入流式响应
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import redis.asyncio as redis
from langchain_community.callbacks.manager import get_openai_callback

from app.workflows.graph import app_graph
from app.core.redis import pool
from app.utils.trace import get_trace_id
from app.workflows.state import apply_read_time_decay
from app.services.memory_service import get_user_profile, update_user_profile

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# Request/Response Schemas
# ============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息内容")
    user_id: Optional[Union[str, int]] = Field(None, description="用户ID")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent 回复内容")
    steps: int = Field(..., description="Agent 思考步数")
    intent: Optional[str] = Field(None, description="识别到的用户意图")
    elapsed_ms: int = Field(..., description="处理耗时（毫秒）")

# ============================================================================
# Endpoints
# ============================================================================

# 🌟 新增：将普通字符串包装为标准 SSE 格式
def format_sse(data: str) -> str:
    """包装为 Server-Sent Events 格式"""
    # 确保内容中的换行不会破坏 SSE 格式
    formatted_data = data.replace('\n', '\\n')
    return f"data: {formatted_data}\n\n"


@router.post("/chat", summary="与 Agent 对话 (Streaming)")
async def chat_with_agent(req: ChatRequest):
    start_time = time.time()
    trace_id = get_trace_id()

    logger.info(f"[API: /chat] [{trace_id}] Received message from user={req.user_id}: {req.message[:50]}...")

    redis_client = redis.Redis(connection_pool=pool)
    msg_hash = hashlib.md5(req.message.encode('utf-8')).hexdigest()
    cache_key = f"carfast:agent:cache:{req.user_id}:{msg_hash}"

    # ==========================================
    # 🌟 统一为单一的流式生成器函数
    # ==========================================
    async def response_generator():
        try:
            # 1. 处理缓存命中场景 (模拟快速的流式输出)
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"[API: /chat] [{trace_id}] 🎯 Redis Cache Hit! 命中语义缓存。")
                resp_dict = json.loads(cached_data)

                # 哪怕是缓存，也要伪装成打字机效果吐给前端，保持接口一致性
                cached_text = resp_dict.get("response", "")
                chunk_size = 5  # 每次吐 5 个字
                for i in range(0, len(cached_text), chunk_size):
                    chunk = cached_text[i:i + chunk_size]
                    yield format_sse(chunk)
                    await asyncio.sleep(0.01)  # 增加微小延迟，增强打字机体感

                yield format_sse("[DONE]")
                return

            # 2. 缓存未命中，走大模型正常流程
            current_profile = {}
            if req.user_id:
                db_memory_dict = await get_user_profile(str(req.user_id))
                if db_memory_dict:
                    current_profile = {
                        "preference_tags": db_memory_dict.get("preference_tags") or [],
                        "preference_brand": db_memory_dict.get("preference_brand"),
                        "budget_min": db_memory_dict.get("budget_min"),
                        "budget_max": db_memory_dict.get("budget_max"),
                    }
                    extra_data = db_memory_dict.get("extra_data") or {}
                    if isinstance(extra_data, dict) and "_meta" in extra_data:
                        current_profile["_meta"] = extra_data["_meta"]
                    current_profile = apply_read_time_decay(current_profile)

            initial_state = {
                "messages": [HumanMessage(content=req.message)],
                "user_id": req.user_id,
                "user_profile": current_profile,
                "step_count": 0
            }

            full_response_text = ""

            with get_openai_callback() as cb:
                async for event in app_graph.astream(
                        initial_state,
                        config={"configurable": {"thread_id": trace_id}},
                        stream_mode="messages"
                ):
                    chunk, metadata = event
                    if metadata.get("langgraph_node") == "chat_generator":
                        if hasattr(chunk, "content") and chunk.content:
                            # 🌟 以标准 SSE 格式吐出实时的字块
                            yield format_sse(chunk.content)
                            full_response_text += chunk.content

                logger.info(f"[{trace_id}] 💰 流式账单结算: Total={cb.total_tokens} tokens")

            # 将完整结果写入缓存
            if full_response_text:
                cache_payload = {"response": full_response_text, "intent": "chat"}
                await redis_client.setex(cache_key, 43200, json.dumps(cache_payload, ensure_ascii=False))

            # 发送结束标识
            yield format_sse("[DONE]")

        except Exception as e:
            logger.error(f"[API: /chat] [{trace_id}] Stream Error: {e}", exc_info=True)
            yield format_sse(f"\n[系统异常]: {str(e)}")
            yield format_sse("[DONE]")

    # 🌟 强制使用 text/event-stream
    return StreamingResponse(response_generator(), media_type="text/event-stream")