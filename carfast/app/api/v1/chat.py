# app/api/v1/chat.py
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from typing import List
from app.utils.jwt import MyJWT
from app.workflows.rag import chat_stream

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # 简单列表存储，生产环境如有多实例需改用 Redis Pub/Sub
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        token: str = Query(..., description="JWT Token required for handshake")
):
    """
    WebSocket AI 导购接口
    Endpoint: ws://domain/api/v1/chat/ws?token=<YOUR_JWT>
    """
    user_id = None

    # -------------------------------------------------------
    # 1. 握手鉴权 (Handshake Auth)
    # -------------------------------------------------------
    try:
        # 验证 Token 有效性
        payload = MyJWT.decode_token(token)
        if not payload or "sub" not in payload:
            logger.warning("WebSocket Auth Failed: Invalid Token")
            # 1008: Policy Violation (RFC 6455)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user_id = int(payload["sub"])
    except Exception as e:
        logger.error(f"WebSocket Auth Error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # -------------------------------------------------------
    # 2. 建立连接
    # -------------------------------------------------------
    await manager.connect(websocket)
    logger.info(f"WebSocket Connected: User {user_id}")

    try:
        while True:
            # 等待用户输入 (文本)
            data = await websocket.receive_text()

            if not data.strip():
                continue

            # -------------------------------------------------------
            # 3. 调用 RAG 大脑 & 推送事件流
            # -------------------------------------------------------
            async for event_json in chat_stream(query=data, user_id=user_id):
                # 检查连接状态 (虽然 send_text 内部会抛出异常，但显式 try 可以更安全)
                await websocket.send_text(event_json)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket Disconnected: User {user_id}")
    except Exception as e:
        logger.error(f"WebSocket Loop Error: {e}")
        manager.disconnect(websocket)
        # 尝试关闭连接
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass