"""
LangGraph Workflow Definition for CarFast Agent.

This module assembles the complete agent graph by connecting
nodes with edges and conditional routing logic.
"""

import logging
from typing import Any, Dict, Literal

from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, BaseMessage

from app.utils.decorators import async_time_it
from app.workflows.state import AgentState
from app.workflows.nodes import identify_intent, execute_search, extract_profile, calculate_executor # 🌟 引入新节点
from app.utils.llm_factory import LLMFactory
from app.config import settings
logger = logging.getLogger(__name__)

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus


try:
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
    milvus_store = Milvus(
        embedding_function=embeddings,
        collection_name=settings.MILVUS_COLLECTION_KNOWLEDGE,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT}
    )
    knowledge_retriever = milvus_store.as_retriever(search_kwargs={"k": 3})
except Exception as e:
    logger.error(f"Milvus 初始化失败: {e}")
    knowledge_retriever = None

# ============================================================================
# System Prompts
# ============================================================================
CHAT_SYSTEM_PROMPT = """你是 CarFast 智能汽车导购助手。

## 角色定位
- 专业、友好的汽车销售顾问
- 擅长根据用户需求推荐合适车辆
- 能够解答汽车相关的各类问题

## 回复原则
1. 必须优先基于提供的【车辆搜索结果】和【行业知识参考】进行回答。
2. 遇到具体的政策、补贴、评测数据，务必使用【行业知识参考】中的内容，不要使用自己的旧知识编造。
3. 💡【重要引用规则】：如果你在回答中使用了【行业知识参考】中的任何内容，必须在最终回答的最末尾另起一行，以 Markdown 格式清晰地附上来源。格式示例：“> 参考知识来源：《xxx》”。如果有多个不同来源，请用逗号隔开。
4. 如果搜索无结果，建议用户调整条件。
5. 使用友好的语气，适当使用 emoji。
"""


# ============================================================================
# Query Rewrite Helper (新增：查询重写)
# ============================================================================

async def rewrite_query(messages: list[BaseMessage]) -> str:
    """
    结合聊天历史重写用户的最新问题，解决指代消解（Coreference Resolution）问题。
    """
    # 过滤出用户的提问
    human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    if not human_msgs:
        return ""

    last_msg = human_msgs[-1].content

    # 如果只有一轮对话，不需要重写，直接返回
    if len(messages) <= 2:
        return last_msg

    try:
        # 使用低温度的小模型保证输出稳定性
        llm = LLMFactory.get_llm(temperature=0.1, streaming=False)

        # 截取最近的 4 条消息作为上下文（避免过长）
        history_text = ""
        for msg in messages[-5:-1]:
            role = "用户" if isinstance(msg, HumanMessage) else "AI"
            history_text += f"{role}: {msg.content[:100]}...\n"  # 截断太长的AI回复

        rewrite_prompt = f"""你的任务是将用户的最新问题，结合前文聊天历史，重写为一个独立的、明确的搜索词。
规则：
1. 如果原问题中包含代词（如“它”、“这个”、“那款车”等），请根据历史替换为具体的车型或事物名称。
2. 如果原问题已经很明确，请直接输出原问题。
3. 必须且只能输出重写后的句子，绝对不要包含任何多余的解释、标点或前导词。

【聊天历史】：
{history_text}

【最新问题】：
{last_msg}

【重写结果】："""

        response = await llm.ainvoke([HumanMessage(content=rewrite_prompt)])
        rewritten = response.content.strip()

        logger.info(f"[Query Rewrite] 原问题: '{last_msg}' -> 重写后: '{rewritten}'")
        return rewritten
    except Exception as e:
        logger.error(f"[Query Rewrite] 重写失败: {e}")
        return last_msg  # 降级：如果失败则使用原问题

# ============================================================================
# Additional Node: Chat Generator
# ============================================================================

@async_time_it
async def chat_generator(state: AgentState) -> Dict[str, Any]:
    logger.info("[Node: chat_generator] Generating response...")

    try:
        llm = LLMFactory.get_llm(temperature=0.3, streaming=False)

        messages = state.get("messages", [])
        tool_output = state.get("tool_output")
        intent = state.get("intent")

        # 1. 提取用户的最后一次提问 (用于兜底展示)
        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        # 2. 【核心升级】：获取重写后的搜索词
        search_query = await rewrite_query(messages)

        # 3. 检索 Milvus 行业知识 (使用重写后的 search_query)
        knowledge_context = ""
        if knowledge_retriever and search_query:
            try:
                docs = await knowledge_retriever.ainvoke(search_query)
                if docs:
                    # 💡 【核心修改】：在这里把元数据（metadata）里的文件名一起喂给大模型
                    knowledge_context = "\n".join([
                        f"- [来源：{doc.metadata.get('source_file', '未知文件')}]\n  内容：{doc.page_content}"
                        for doc in docs
                    ])
            except Exception as e:
                logger.error(f"Milvus 检索失败: {e}")

        # 4. 构造 Prompt
        llm_messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]

        for msg in messages:
            llm_messages.append(msg)

        if tool_output:
            # 🌟 动态标题：告诉大模型这到底是库存数据，还是算账结果
            context_title = "车辆搜索结果 (库存)" if intent == "search" else "工具执行结果"
            llm_messages.append(SystemMessage(
                content=f"## {context_title}\n{tool_output}"
            ))

        if knowledge_context:
            llm_messages.append(SystemMessage(
                content=f"## 行业知识参考 (政策/评测)\n请结合以下最新信息回答：\n{knowledge_context}"
            ))

        response = await llm.ainvoke(llm_messages)
        ai_message = AIMessage(content=response.content)

        return {"messages": [ai_message], "step_count": 1}

    except Exception as e:
        error_response = AIMessage(content=f"抱歉，我遇到了一点问题，请稍后再试。({str(e)})")
        logger.error(f"[Node: chat_generator] Error: {e}", exc_info=True)
        return {"messages": [error_response], "step_count": 1}


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
    elif intent == "calculate":
        return "calculate_executor"
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
    workflow.add_node("calculate_executor", calculate_executor)  # 🌟 注册节点
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
            "calculate_executor": "calculate_executor",  # 🌟 路由映射
            "chat_generator": "chat_generator"
        }
    )

    workflow.add_edge("search_executor", "chat_generator")
    workflow.add_edge("calculate_executor", "chat_generator")
    
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
