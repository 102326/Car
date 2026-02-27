"""
Agent API Endpoints for CarFast.
This module exposes the LangGraph agent via FastAPI REST endpoints.
"""

import logging
import time
import hashlib
import json
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import redis.asyncio as redis
# 🌟 引入 LangChain 官方的 Token 追踪回调
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
# Helper Functions
# ============================================================================

def extract_last_ai_message(messages: List[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg.content
    return "[Agent 未生成回复]"

# ============================================================================
# Endpoints
# ============================================================================

@router.post("/chat", response_model=ChatResponse, summary="与 Agent 对话")
async def chat_with_agent(req: ChatRequest) -> ChatResponse:
    start_time = time.time()
    trace_id = get_trace_id()

    logger.info(f"[API: /chat] [{trace_id}] Received message from user={req.user_id}: {req.message[:50]}...")

    try:
        redis_client = redis.Redis(connection_pool=pool)

        # 1. 生成唯一的 Cache Key (组合 user_id 和 消息内容的 MD5 哈希)
        msg_hash = hashlib.md5(req.message.encode('utf-8')).hexdigest()
        cache_key = f"carfast:agent:cache:{req.user_id}:{msg_hash}"

        # 2. 尝试拦截：查询 Redis 缓存
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"[API: /chat] [{trace_id}] 🎯 Redis Cache Hit! 命中语义缓存，大模型零消耗。")
            resp_dict = json.loads(cached_data)

            elapsed_ms = int((time.time() - start_time) * 1000)
            return ChatResponse(
                response=resp_dict["response"],
                steps=0,
                intent=resp_dict.get("intent", "cache_hit"),
                elapsed_ms=elapsed_ms
            )

        # 3. 缓存未命中，组装初始状态，进入 LangGraph 运转
        # ==========================================
        # 🌟 真实业务环境：从数据库加载并触发"读时衰减"
        # ==========================================
        current_profile = {}
        if req.user_id:
            # ✅ 调用 get_user_profile，它返回的是一个字典
            db_memory_dict = await get_user_profile(str(req.user_id))

            if db_memory_dict:
                current_profile = {
                    "preference_tags": db_memory_dict.get("preference_tags") or [],
                    "preference_brand": db_memory_dict.get("preference_brand"),
                    "budget_min": db_memory_dict.get("budget_min"),
                    "budget_max": db_memory_dict.get("budget_max"),
                }
                # 提取权重的隐藏元数据 (Meta)
                extra_data = db_memory_dict.get("extra_data") or {}
                if isinstance(extra_data, dict) and "_meta" in extra_data:
                    current_profile["_meta"] = extra_data["_meta"]

                # 🚀 触发工业级读时衰减 (Read-time Decay)
                current_profile = apply_read_time_decay(current_profile)

        initial_state = {
            "messages": [HumanMessage(content=req.message)],
            "user_id": req.user_id,
            "user_profile": current_profile,  # 传入经过岁月冲刷的最新画像
            "step_count": 0
        }

        # 🌟 核心修改：使用 Token 回调管理器包裹整个图的执行过程
        with get_openai_callback() as cb:
            result = await app_graph.ainvoke(initial_state)

            # 自定义计算预估成本 (假设按目前主流国产大模型定价：输入约1元/百万Token，输出约2元/百万Token)
            estimated_cost = (cb.prompt_tokens * 1.0 + cb.completion_tokens * 2.0) / 1000000

            logger.info(
                f"[API: /chat] [{trace_id}] 💰 算力账单: "
                f"Prompt={cb.prompt_tokens} | Completion={cb.completion_tokens} | "
                f"Total={cb.total_tokens} | 预估成本: ¥{estimated_cost:.6f}"
            )

            # 提取图运转后的最终数据
            final_messages = result.get("messages", [])
            response_text = extract_last_ai_message(final_messages)
            step_count = result.get("step_count", 0)
            intent = result.get("intent")

            # ==========================================
            # 🌟 核心补丁：持久化记忆元数据 (Meta)
            # 把 LangGraph 算好的最新衰减权重，存回数据库的 extra_data 字段
            # ==========================================
            final_profile = result.get("user_profile", {})
            if req.user_id and "_meta" in final_profile:
                await update_user_profile(
                    user_id=str(req.user_id),
                    data={"extra_data": {"_meta": final_profile["_meta"]}}
                )
                logger.info(f"[API: /chat] [{trace_id}] 🧠 用户潜意识(Meta)已持久化到数据库。")

        # 4. 异步将昂贵的大模型结果写入缓存 (设置 12 小时自动过期 TTL)
        cache_payload = {
            "response": response_text,
            "intent": intent
        }
        await redis_client.setex(cache_key, 43200, json.dumps(cache_payload, ensure_ascii=False))

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"[API: /chat] [{trace_id}] Completed | intent={intent} | steps={step_count} | "
            f"elapsed={elapsed_ms}ms | response_len={len(response_text)}"
        )

        return ChatResponse(
            response=response_text,
            steps=step_count,
            intent=intent,
            elapsed_ms=elapsed_ms
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[API: /chat] [{trace_id}] Error after {elapsed_ms}ms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent 执行失败: {str(e)}")

@router.get("/health", summary="Agent 健康检查")
async def agent_health() -> Dict[str, Any]:
    return {"status": "healthy", "agent": "CarFast LangGraph Agent", "version": "1.0.0"}