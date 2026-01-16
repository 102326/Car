# app/agents/state.py
"""
定义 LangGraph 的状态管理
"""
from typing import TypedDict, List, Optional, Dict, Any
from typing_extensions import Annotated
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class UserProfile(TypedDict):
    """用户画像"""
    budget_min: Optional[float]  # 预算下限（万元）
    budget_max: Optional[float]  # 预算上限（万元）
    city: Optional[str]  # 所在城市
    preferences: Dict[str, Any]  # 偏好: {"energy_type": "纯电", "level": "SUV", "brand": "比亚迪"}
    purchase_intent: Optional[str]  # 购车意图: "family" / "business" / "sport"
    is_first_car: Optional[bool]  # 是否首次购车


class AgentState(TypedDict):
    """
    主 Agent 状态
    - messages: 使用 add_messages 注解实现自动追加消息历史
    - user_profile: 从对话中提取的用户画像
    - next_step: 下一步路由的动作
    - rag_context: RAG 检索到的上下文
    - enrichment_result: 数据补充结果
    - final_answer: 最终回复给用户的答案
    """
    # 自动追加消息历史（核心功能）
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 用户画像
    user_profile: UserProfile
    
    # 路由控制
    next_step: str  # "rag" / "enrichment" / "trade" / "chat" / "end"
    
    # 各节点的数据
    rag_context: Optional[str]
    enrichment_result: Optional[Dict[str, Any]]
    trade_info: Optional[Dict[str, Any]]
    
    # 最终答案
    final_answer: Optional[str]
    
    # 元数据
    metadata: Optional[Dict[str, Any]]  # 存放调试信息、耗时统计等
