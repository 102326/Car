from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.workflows.rag import rag_app

chat_router = APIRouter(prefix="/chat", tags=["AI 智能客服"])

@chat_router.post("", response_model=ChatResponse)
async def ai_chat(request: ChatRequest):
    try:
        # 调用 RAG 工作流
        result = await rag_app.ainvoke({"question": request.message})
        return ChatResponse(answer=result["answer"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
