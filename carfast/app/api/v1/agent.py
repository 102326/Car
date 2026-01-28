"""
Agent API Endpoints for CarFast.

This module exposes the LangGraph agent via FastAPI REST endpoints.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.workflows.graph import app_graph

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息内容")
    user_id: Optional[Union[str, int]] = Field(None, description="用户ID（可选，支持字符串或整数）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "有没有30万以内的宝马SUV？",
                    "user_id": "user_12345"
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    response: str = Field(..., description="Agent 回复内容")
    steps: int = Field(..., description="Agent 思考步数")
    intent: Optional[str] = Field(None, description="识别到的用户意图")
    elapsed_ms: int = Field(..., description="处理耗时（毫秒）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "为您找到以下符合条件的车辆...",
                    "steps": 3,
                    "intent": "search",
                    "elapsed_ms": 1523
                }
            ]
        }
    }


# ============================================================================
# Helper Functions
# ============================================================================

def extract_last_ai_message(messages: List[BaseMessage]) -> str:
    """
    Extract content from the last AIMessage in the message list.
    
    Args:
        messages: List of messages from agent state.
        
    Returns:
        Content string from the last AI message, or error message if not found.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg.content
    return "[Agent 未生成回复]"


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/chat", response_model=ChatResponse, summary="与 Agent 对话")
async def chat_with_agent(req: ChatRequest) -> ChatResponse:
    """
    与 CarFast 智能导购 Agent 进行对话。
    
    Agent 会自动识别用户意图：
    - **search**: 查找车辆，返回库存推荐
    - **chat**: 普通对话，回答问题
    - **calculate**: 费用计算（开发中）
    
    Args:
        req: Chat request containing user message.
        
    Returns:
        ChatResponse with agent reply and metadata.
        
    Raises:
        HTTPException: If agent execution fails.
    """
    start_time = time.time()
    
    logger.info(f"[API: /chat] Received message from user={req.user_id}: {req.message[:50]}...")
    
    try:
        # Build initial state
        initial_state = {
            "messages": [HumanMessage(content=req.message)],
            "user_id": req.user_id,
            "user_profile": {},
            "step_count": 0
        }
        
        # Invoke agent graph
        result = await app_graph.ainvoke(initial_state)
        
        # Calculate elapsed time
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Extract response from final state
        final_messages = result.get("messages", [])
        response_text = extract_last_ai_message(final_messages)
        
        # Get metadata
        step_count = result.get("step_count", 0)
        intent = result.get("intent")
        
        logger.info(
            f"[API: /chat] Completed | intent={intent} | steps={step_count} | "
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
        logger.error(f"[API: /chat] Error after {elapsed_ms}ms: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Agent 执行失败: {str(e)}"
        )


@router.get("/health", summary="Agent 健康检查")
async def agent_health() -> Dict[str, Any]:
    """
    检查 Agent 服务状态。
    
    Returns:
        Health status dict.
    """
    return {
        "status": "healthy",
        "agent": "CarFast LangGraph Agent",
        "version": "1.0.0"
    }
