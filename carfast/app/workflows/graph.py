"""
LangGraph Workflow Definition for CarFast Agent.

This module assembles the complete agent graph by connecting
nodes with edges and conditional routing logic.
"""

import logging
from typing import Any, Dict, Literal

from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage, SystemMessage

from app.workflows.state import AgentState
from app.workflows.nodes import identify_intent, execute_search, extract_profile
from app.utils.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


# ============================================================================
# System Prompts
# ============================================================================

CHAT_SYSTEM_PROMPT = """你是 CarFast 智能汽车导购助手。

## 角色定位
- 专业、友好的汽车销售顾问
- 擅长根据用户需求推荐合适车辆
- 能够解答汽车相关的各类问题

## 回复原则
1. 简洁明了，避免冗长
2. 如果有搜索结果，优先基于结果推荐
3. 引导用户提供更多需求信息（预算、用途、偏好等）
4. 使用友好的语气，适当使用 emoji

## 特殊情况
- 如果用户询问计算类问题（分期、保险），礼貌告知该功能即将上线
- 如果搜索无结果，建议用户调整条件
"""


# ============================================================================
# Additional Node: Chat Generator
# ============================================================================

async def chat_generator(state: AgentState) -> Dict[str, Any]:
    """
    Chat Generation Node: Generate final response using LLM.
    
    This node:
    1. Gets LLM instance
    2. Builds context from state (messages + tool_output if available)
    3. Generates natural language response
    
    Args:
        state: Current agent state.
        
    Returns:
        Dict with 'messages' containing the AI response.
    """
    logger.info("[Node: chat_generator] Generating response...")
    
    try:
        # Get LLM instance
        llm = LLMFactory.get_llm(temperature=0.7, streaming=False)
        
        # Build messages for LLM
        messages = state.get("messages", [])
        tool_output = state.get("tool_output")
        intent = state.get("intent")
        
        # Construct prompt messages
        llm_messages = [
            SystemMessage(content=CHAT_SYSTEM_PROMPT),
        ]
        
        # Add conversation history
        for msg in messages:
            llm_messages.append(msg)
        
        # If we have search results, inject them as context
        if tool_output:
            context_msg = SystemMessage(
                content=f"""## 车辆搜索结果
以下是根据用户需求查询到的库存信息，请基于此结果为用户提供推荐和建议：

{tool_output}

请根据上述搜索结果，用自然、友好的语言回复用户。突出精选车源的亮点，并给出购买建议。"""
            )
            llm_messages.append(context_msg)
        
        # Handle calculate intent (feature not ready)
        if intent == "calculate":
            llm_messages.append(
                SystemMessage(content="[系统提示] 用户想要进行费用计算，但该功能暂未上线，请礼貌告知。")
            )
        
        # Invoke LLM
        logger.debug(f"[Node: chat_generator] Invoking LLM with {len(llm_messages)} messages")
        response = await llm.ainvoke(llm_messages)
        
        # Wrap response as AIMessage
        ai_message = AIMessage(content=response.content)
        
        logger.info(f"[Node: chat_generator] Response generated, length: {len(response.content)} chars")
        
        return {
            "messages": [ai_message],
            "step_count": 1
        }
        
    except Exception as e:
        error_response = AIMessage(content=f"抱歉，我遇到了一点问题，请稍后再试。({str(e)})")
        logger.error(f"[Node: chat_generator] Error: {e}", exc_info=True)
        
        return {
            "messages": [error_response],
            "step_count": 1
        }


# ============================================================================
# Conditional Edge Function
# ============================================================================

def route_by_intent(state: AgentState) -> Literal["search_executor", "chat_generator"]:
    """
    Route to the next node based on classified intent.
    
    Args:
        state: Current agent state containing intent.
        
    Returns:
        Name of the next node to execute.
    """
    intent = state.get("intent", "chat")
    
    logger.info(f"[Router] Routing based on intent: {intent}")
    
    if intent == "search":
        return "search_executor"
    else:
        # Both "chat" and "calculate" go to chat_generator
        # calculate is handled gracefully inside chat_generator
        return "chat_generator"


# ============================================================================
# Graph Construction
# ============================================================================

def build_graph() -> StateGraph:
    """
    Build and return the complete agent workflow graph.
    
    Graph Structure:
    
        START
          │
          ▼
    ┌─────────────────┐
    │profile_extractor│
    └────────┬────────┘
             │
             ▼
    ┌─────────────┐
    │intent_router│
    └─────┬───────┘
          │
          ├── intent="search" ──► search_executor ──┐
          │                                         │
          └── intent="chat"/"calculate" ───────────►├──► chat_generator ──► END
    
    Returns:
        Compiled StateGraph ready for execution.
    """
    logger.info("[Graph] Building workflow graph...")
    
    # Initialize StateGraph with AgentState schema
    workflow = StateGraph(AgentState)
    
    # ========== Add Nodes ==========
    workflow.add_node("profile_extractor", extract_profile)
    workflow.add_node("intent_router", identify_intent)
    workflow.add_node("search_executor", execute_search)
    workflow.add_node("chat_generator", chat_generator)
    
    # ========== Add Edges ==========
    
    # Entry point: START -> profile_extractor
    workflow.add_edge(START, "profile_extractor")
    
    # Flow: profile_extractor -> intent_router
    workflow.add_edge("profile_extractor", "intent_router")
    
    # Conditional edge: intent_router -> (search_executor | chat_generator)
    workflow.add_conditional_edges(
        source="intent_router",
        path=route_by_intent,
        path_map={
            "search_executor": "search_executor",
            "chat_generator": "chat_generator"
        }
    )
    
    # After search, generate response: search_executor -> chat_generator
    workflow.add_edge("search_executor", "chat_generator")
    
    # Terminal edge: chat_generator -> END
    workflow.add_edge("chat_generator", END)
    
    logger.info("[Graph] Workflow graph built successfully")
    
    return workflow


# ============================================================================
# Compile and Export
# ============================================================================

# Build the workflow graph
_workflow = build_graph()

# Compile the graph for execution
app_graph = _workflow.compile()

logger.info("[Graph] CarFast Agent graph compiled and ready")
