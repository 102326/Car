"""
LangGraph 工作流定义文件 (CarFast Agent)

该模块负责组装完整的智能体有向无环图 (DAG)，
通过定义节点 (Nodes)、边 (Edges) 以及条件路由 (Conditional Routing)
来实现大模型与各种工具的联动。
"""

import logging
from typing import Any, Dict, Literal
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, BaseMessage

from app.utils.decorators import async_time_it
from app.workflows.state import AgentState
from app.workflows.nodes import (
    identify_intent,
    execute_search,
    extract_profile,
    calculate_executor,
    calculate_critic # 🌟 引入风控审核节点
)
from app.utils.llm_factory import LLMFactory
from app.config import settings
logger = logging.getLogger(__name__)

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus

# ----------------------------------------------------------------------------
# 向量数据库初始化 (Milvus)
# ----------------------------------------------------------------------------
try:
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
    milvus_store = Milvus(
        embedding_function=embeddings,
        collection_name=settings.MILVUS_COLLECTION_KNOWLEDGE,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT}
    )
    # k=3 表示召回最相关的 3 个 Chunk
    knowledge_retriever = milvus_store.as_retriever(search_kwargs={"k": 3})
except Exception as e:
    logger.error(f"Milvus 初始化失败: {e}")
    knowledge_retriever = None

# ============================================================================
# System Prompts (系统提示词)
# ============================================================================
CHAT_SYSTEM_PROMPT = """你是 CarFast 智能汽车导购助手。

## 角色定位
- 专业、严谨且友好的汽车销售顾问。
- 擅长根据用户需求推荐合适车辆，并解答汽车、金融相关的各类问题。

## 回复原则
1. 必须优先基于系统提供的【车辆搜索结果】或【系统工具与风控执行结果】进行回答。
2. 遇到具体的政策、补贴、评测数据，务必使用【行业知识参考】中的内容，绝对不要利用过时记忆进行幻觉编造。
3. 💡【重要引用规则】：如果你在回答中使用了【行业知识参考】中的任何内容，必须在最终回答的最末尾另起一行，以 Markdown 格式清晰地附上来源。格式示例：“> 参考知识来源：《xxx.md》”。
4. 使用友好的语气，适当使用 emoji 提升对话体验。
"""

# ============================================================================
# 查询重写模块 (Query Rewrite)
# ============================================================================
async def rewrite_query(messages: list[BaseMessage]) -> str:
    """
    Query Rewrite: 结合历史聊天上下文，将用户最新提问重写为无代词的独立搜索词。
    主要用于解决多轮对话 RAG 检索时的指代消解 (Coreference Resolution) 问题。
    """
    human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    if not human_msgs:
        return ""

    last_msg = human_msgs[-1].content

    # 如果只有一轮对话，无上下文依赖，直接返回原句
    if len(messages) <= 2:
        return last_msg

    try:
        # 使用低温度 (0.1) 保证重写结果的客观性和稳定性
        llm = LLMFactory.get_llm(temperature=0.1, streaming=False)

        # 截取最近 4 条消息作为上下文
        history_text = ""
        for msg in messages[-5:-1]:
            role = "用户" if isinstance(msg, HumanMessage) else "AI"
            history_text += f"{role}: {msg.content[:100]}...\n"

        rewrite_prompt = f"""你的任务是将用户的最新问题，结合前文聊天历史，重写为一个独立的、明确的搜索词。
规则：
1. 如果原问题中包含代词（如“它”、“这个”、“那款车”），请根据历史替换为具体的车型或事物名称。
2. 必须且只能输出重写后的句子，绝对不要包含多余的解释或前导词。

【聊天历史】：\n{history_text}\n
【最新问题】：\n{last_msg}\n
【重写结果】："""

        response = await llm.ainvoke([HumanMessage(content=rewrite_prompt)])
        rewritten = response.content.strip()

        logger.info(f"[Query Rewrite] 原问题: '{last_msg}' -> 重写后: '{rewritten}'")
        return rewritten
    except Exception as e:
        logger.error(f"[Query Rewrite] 重写失败，降级返回原句: {e}")
        return last_msg


# ============================================================================
# 聊天生成节点 (Generator Node)
# ============================================================================
@async_time_it
# 🌟 修改 1：在参数中增加 config: RunnableConfig，接收外层传进来的流式回调钩子
async def chat_generator(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    logger.info("[Node: chat_generator] Generating response...")

    try:
        # 🌟 修改 2：务必将 streaming 改为 True，让底层模型开启打字机模式
        llm = LLMFactory.get_llm(temperature=0.3, streaming=True)

        messages = state.get("messages", [])
        tool_output = state.get("tool_output")
        intent = state.get("intent")

        # 获取风控审核结果
        critic_decision = state.get("critic_decision")
        critic_reason = state.get("critic_reason")

        search_query = await rewrite_query(messages)

        # ... (Milvus RAG 检索部分保持不变) ...
        knowledge_context = ""
        if knowledge_retriever and search_query:
            try:
                docs = await knowledge_retriever.ainvoke(search_query)
                if docs:
                    knowledge_context = "\n".join([
                        f"- [来源：{doc.metadata.get('source_file', '未知文件')}]\n  内容：{doc.page_content}"
                        for doc in docs
                    ])
            except Exception as e:
                logger.error(f"Milvus 检索异常: {e}")

        # 3. 组装最终的 LLM Context
        llm_messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]

        for msg in messages:
            llm_messages.append(msg)

        # ==========================================
        # 核心分发：依据风控决策来决定喂给大模型什么数据
        # ==========================================
        if critic_decision == "reject":
            llm_messages.append(SystemMessage(
                content=f"## 🛑 风控审核拦截通知\n"
                        f"用户的购车/贷款方案请求已被金融风控系统拦截！\n"
                        f"拦截原因：{critic_reason}\n\n"
                        f"【系统强制指令】：请你委婉、礼貌地告知用户该方案无法在现实中获批，并结合拦截原因给出合理的行业建议（例如推荐首付20%以上）。**绝对不要**向用户展示任何系统底层计算出的月供数字，因为该方案本身无效！"
            ))
        elif tool_output:
            context_title = "车辆库存搜索结果" if intent == "search" else "系统工具与计算结果"
            llm_messages.append(SystemMessage(
                content=f"## {context_title}\n{tool_output}"
            ))

        if knowledge_context:
            llm_messages.append(SystemMessage(
                content=f"## 行业知识参考 (政策/评测)\n请结合以下最新信息回答：\n{knowledge_context}"
            ))

        # ==========================================
        # 🌟 修改 3：极其核心的接力！把 config 传给 ainvoke。
        # 这样大模型每吐出一个字，都会顺着 config 流向前端，而不是憋在内存里等 30 秒！
        # ==========================================
        response = await llm.ainvoke(llm_messages, config=config)

        ai_message = AIMessage(content=response.content)

        return {"messages": [ai_message], "step_count": 1}

    except Exception as e:
        error_response = AIMessage(content=f"抱歉，系统生成回复时遇到问题，请稍后再试。({str(e)})")
        logger.error(f"[Node: chat_generator] Error: {e}", exc_info=True)
        return {"messages": [error_response], "step_count": 1}

    
# ============================================================================
# 条件路由控制 (Conditional Router)
# ============================================================================
def route_by_intent(state: AgentState) -> Literal["search_executor", "calculate_executor", "chat_generator"]:
    """
    核心路由函数：根据 identify_intent 节点输出的分类结果，
    决定将数据流向查询引擎、计算引擎还是直接聊天。
    """
    intent = state.get("intent", "chat")
    logger.info(f"[Router] Routing based on intent: {intent}")

    if intent == "search":
        return "search_executor"
    elif intent == "calculate":
        return "calculate_executor"
    else:
        # Default to chat
        return "chat_generator"

# ============================================================================
# 工作流构建 (Graph Construction)
# ============================================================================
def build_graph() -> StateGraph:
    """
    构建并返回完整的 Agent StateGraph (DAG)。

    【架构拓扑图】:
        START
          │
          ▼
    ┌─────────────────┐
    │profile_extractor│ (画像提取)
    └────────┬────────┘
             │
             ▼
    ┌─────────────┐
    │intent_router│ (意图路由)
    └─────┬───────┘
          │
          ├── intent="search" ──► search_executor (查库存) ─────────┐
          │                                                         │
          ├── intent="calculate" ──► calculate_executor (算贷款)    │
          │                                │                        │
          │                                ▼                        │
          │                         calculate_critic (风控拦截) ────┤
          │                                                         │
          └── intent="chat" ────────────────────────────────────────►├──► chat_generator ──► END
    """
    logger.info("[Graph] Building workflow graph...")

    workflow = StateGraph(AgentState)

    # ---------- 1. 注册所有的 Node ----------
    workflow.add_node("profile_extractor", extract_profile)
    workflow.add_node("intent_router", identify_intent)
    workflow.add_node("search_executor", execute_search)
    workflow.add_node("calculate_executor", calculate_executor)
    workflow.add_node("calculate_critic", calculate_critic)  # 🌟 注册风控审核员
    workflow.add_node("chat_generator", chat_generator)

    # ---------- 2. 定义静态流转 Edges ----------
    # 入口链路
    workflow.add_edge(START, "profile_extractor")
    workflow.add_edge("profile_extractor", "intent_router")

    # ---------- 3. 定义动态路由分支 ----------
    workflow.add_conditional_edges(
        source="intent_router",
        path=route_by_intent,
        path_map={
            "search_executor": "search_executor",
            "calculate_executor": "calculate_executor",
            "chat_generator": "chat_generator"
        }
    )

    # ---------- 4. 业务收口连线 ----------
    # 搜索完成后，直接去生成话术
    workflow.add_edge("search_executor", "chat_generator")

    # 🌟 修复核心 Bug：计算器算完后，绝对不能直接对话用户，必须先过风控！
    workflow.add_edge("calculate_executor", "calculate_critic")
    workflow.add_edge("calculate_critic", "chat_generator")

    # 终局流转
    workflow.add_edge("chat_generator", END)

    logger.info("[Graph] Workflow graph built successfully")
    return workflow

# ============================================================================
# 编译并暴露图实例
# ============================================================================
_workflow = build_graph()
app_graph = _workflow.compile()
logger.info("[Graph] CarFast Agent graph compiled and ready")