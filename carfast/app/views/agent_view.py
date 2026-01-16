# app/views/agent_view.py
"""
智能购车管家 API 接口
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json

from app.agents.smart_car_concierge import create_smart_car_concierge

router = APIRouter(prefix="/api/agent", tags=["智能购车管家"])

# 内存存储会话状态（生产环境应使用Redis）
session_store: Dict[str, Dict[str, Any]] = {}


# ==========================================
# Pydantic Schemas
# ==========================================
class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, description="会话ID（用于保持上下文）")
    stream: bool = Field(False, description="是否流式返回")


class ChatResponse(BaseModel):
    """对话响应"""
    answer: str = Field(..., description="AI回复内容")
    session_id: str = Field(..., description="会话ID")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="用户画像")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


# ==========================================
# API Endpoints
# ==========================================
@router.post("/chat", response_model=ChatResponse, summary="智能对话")
async def chat(request: ChatRequest):
    """
    智能购车管家对话接口
    
    功能:
        - 自动识别用户意图
        - RAG检索知识库
        - 数据补充
        - 交易处理
    
    示例:
        ```json
        {
            "message": "20万左右的SUV有哪些推荐",
            "session_id": "user_12345"
        }
        ```
    """
    try:
        # 创建 Agent 实例
        agent = create_smart_car_concierge()
        
        # 获取会话状态
        session_id = request.session_id or f"session_{id(request)}"
        session_state = session_store.get(session_id)
        
        # 执行对话
        result = await agent.chat(
            user_input=request.message,
            session_state=session_state
        )
        
        # 保存会话状态
        session_store[session_id] = result["state"]
        
        return ChatResponse(
            answer=result["answer"],
            session_id=session_id,
            user_profile=result["metadata"].get("user_profile"),
            metadata=result["metadata"]
        )
        
    except Exception as e:
        print(f"[AgentView] 对话异常: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")


@router.post("/chat/stream", summary="流式对话")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口（SSE）
    
    适用于需要实时显示生成过程的场景
    """
    try:
        agent = create_smart_car_concierge()
        
        session_id = request.session_id or f"session_{id(request)}"
        session_state = session_store.get(session_id)
        
        async def event_generator():
            """SSE事件生成器"""
            try:
                async for event in agent.stream_chat(request.message, session_state):
                    # 将事件转换为SSE格式
                    event_data = json.dumps(event, ensure_ascii=False)
                    yield f"data: {event_data}\n\n"
                
                # 发送结束标记
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {error_data}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式对话失败: {str(e)}")


@router.delete("/session/{session_id}", summary="清除会话")
async def clear_session(session_id: str):
    """
    清除会话状态
    
    用于用户退出或重置对话
    """
    if session_id in session_store:
        del session_store[session_id]
        return {"message": "会话已清除", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/session/{session_id}/profile", summary="获取用户画像")
async def get_user_profile(session_id: str):
    """
    获取当前会话的用户画像
    
    用于前端展示用户偏好、预算等信息
    """
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    state = session_store[session_id]
    user_profile = state.get("user_profile", {})
    
    return {
        "session_id": session_id,
        "user_profile": user_profile
    }


@router.get("/health", summary="健康检查")
async def health_check():
    """
    Agent 健康检查
    
    返回:
        - agent_status: Agent状态
        - active_sessions: 活跃会话数
    """
    return {
        "agent_status": "healthy",
        "active_sessions": len(session_store),
        "version": "1.0.0"
    }


# ==========================================
# 测试端点（仅开发环境使用）
# ==========================================
@router.post("/test/intent", summary="[测试] 意图识别")
async def test_intent(message: str):
    """
    测试意图识别节点
    
    用于调试路由逻辑
    """
    from app.agents.nodes import intent_router_node
    from app.agents.state import AgentState, UserProfile
    from langchain_core.messages import HumanMessage
    
    test_state = AgentState(
        messages=[HumanMessage(content=message)],
        user_profile=UserProfile(
            budget_min=None,
            budget_max=None,
            city=None,
            preferences={},
            purchase_intent=None,
            is_first_car=None
        ),
        next_step="",
        rag_context=None,
        enrichment_result=None,
        trade_info=None,
        final_answer=None,
        metadata={}
    )
    
    result = await intent_router_node(test_state)
    
    return {
        "message": message,
        "intent": result.get("next_step"),
        "user_profile": result.get("user_profile"),
        "metadata": result.get("metadata")
    }
