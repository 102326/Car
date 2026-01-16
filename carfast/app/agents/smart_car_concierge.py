# app/agents/smart_car_concierge.py
"""
智能购车管家主 Agent
使用 LangGraph 的 StateGraph 实现多节点协同
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agents.state import AgentState, UserProfile
from app.agents.nodes import (
    intent_router_node,
    rag_node,
    data_enrichment_node,
    trade_node,
    chat_node
)
from app.agents.prompts import SMART_CAR_CONCIERGE_SYSTEM_PROMPT


class SmartCarConciergeAgent:
    """
    智能购车管家主 Agent
    
    架构模式: Supervisor + StateGraph
    工作流程:
        用户输入 -> Intent Router -> RAG/Enrichment/Trade/Chat -> 返回结果
    """
    
    def __init__(self):
        self.graph = self._build_graph()
        self.system_prompt = SMART_CAR_CONCIERGE_SYSTEM_PROMPT
    
    def _build_graph(self) -> StateGraph:
        """
        构建 LangGraph 状态图
        
        节点:
            - intent_router: 意图识别
            - rag: RAG检索生成
            - enrichment: 数据补充
            - trade: 交易处理
            - chat: 闲聊
        
        边:
            - 条件边: 根据 next_step 动态路由
        """
        # 创建状态图
        workflow = StateGraph(AgentState)
        
        # ==========================================
        # 添加节点
        # ==========================================
        workflow.add_node("intent_router", intent_router_node)
        workflow.add_node("rag", rag_node)
        workflow.add_node("enrichment", data_enrichment_node)
        workflow.add_node("trade", trade_node)
        workflow.add_node("chat", chat_node)
        
        # ==========================================
        # 设置入口点（首先进入意图识别）
        # ==========================================
        workflow.set_entry_point("intent_router")
        
        # ==========================================
        # 添加条件边（核心路由逻辑）
        # ==========================================
        workflow.add_conditional_edges(
            "intent_router",
            self._route_after_intent,  # 路由函数
            {
                "rag": "rag",
                "enrichment": "enrichment",
                "trade": "trade",
                "chat": "chat",
                "end": END
            }
        )
        
        # RAG节点之后的路由（可能需要数据补充）
        workflow.add_conditional_edges(
            "rag",
            self._route_after_rag,
            {
                "enrichment": "enrichment",
                "end": END
            }
        )
        
        # 其他节点直接结束
        workflow.add_edge("enrichment", END)
        workflow.add_edge("trade", END)
        workflow.add_edge("chat", END)
        
        # ==========================================
        # 编译图
        # ==========================================
        return workflow.compile()
    
    @staticmethod
    def _route_after_intent(state: AgentState) -> Literal["rag", "enrichment", "trade", "chat", "end"]:
        """
        意图识别后的路由决策
        
        根据 state["next_step"] 决定下一个节点
        """
        next_step = state.get("next_step", "rag")
        print(f"[Route] Intent Router -> {next_step}")
        return next_step
    
    @staticmethod
    def _route_after_rag(state: AgentState) -> Literal["enrichment", "end"]:
        """
        RAG节点后的路由决策
        
        如果 RAG 检索结果为空或质量差，路由到数据补充节点
        """
        next_step = state.get("next_step", "end")
        
        # 如果 next_step 明确要求 enrichment，则路由
        if next_step == "enrichment":
            print(f"[Route] RAG -> enrichment (检索结果不足)")
            return "enrichment"
        
        print(f"[Route] RAG -> END")
        return "end"
    
    async def chat(self, user_input: str, session_state: dict = None) -> dict:
        """
        主对话接口
        
        Args:
            user_input: 用户输入的消息
            session_state: 会话状态（包含历史消息、用户画像等）
        
        Returns:
            {
                "answer": "AI回复内容",
                "state": "更新后的会话状态",
                "metadata": "调试信息"
            }
        """
        # ==========================================
        # 初始化状态
        # ==========================================
        if session_state is None:
            # 新会话，添加系统提示
            initial_state = {
                "messages": [SystemMessage(content=self.system_prompt)],
                "user_profile": UserProfile(
                    budget_min=None,
                    budget_max=None,
                    city=None,
                    preferences={},
                    purchase_intent=None,
                    is_first_car=None
                ),
                "next_step": "intent_router",
                "rag_context": None,
                "enrichment_result": None,
                "trade_info": None,
                "final_answer": None,
                "metadata": {}
            }
        else:
            initial_state = session_state.copy()
        
        # 添加用户消息
        initial_state["messages"].append(HumanMessage(content=user_input))
        
        # ==========================================
        # 执行图
        # ==========================================
        try:
            # LangGraph 自动管理状态传递
            final_state = await self.graph.ainvoke(initial_state)
            
            # 提取最终答案
            answer = final_state.get("final_answer", "抱歉，我暂时无法回答这个问题。")
            
            # 将AI回复添加到消息历史
            final_state["messages"].append(AIMessage(content=answer))
            
            # 返回结果
            return {
                "answer": answer,
                "state": final_state,  # 保存状态供下次对话使用
                "metadata": {
                    "user_profile": final_state.get("user_profile"),
                    "intent": final_state.get("metadata", {}).get("intent_reasoning"),
                    "rag_context_length": len(final_state.get("rag_context", ""))
                }
            }
            
        except Exception as e:
            print(f"[SmartCarConcierge] 执行异常: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "answer": "抱歉，系统出现了一点问题，请稍后再试或联系客服。",
                "state": initial_state,
                "metadata": {"error": str(e)}
            }
    
    async def stream_chat(self, user_input: str, session_state: dict = None):
        """
        流式对话接口（支持实时输出）
        
        Args:
            user_input: 用户输入
            session_state: 会话状态
        
        Yields:
            每个节点的执行结果
        """
        if session_state is None:
            initial_state = {
                "messages": [SystemMessage(content=self.system_prompt)],
                "user_profile": UserProfile(
                    budget_min=None,
                    budget_max=None,
                    city=None,
                    preferences={},
                    purchase_intent=None,
                    is_first_car=None
                ),
                "next_step": "intent_router",
                "rag_context": None,
                "enrichment_result": None,
                "trade_info": None,
                "final_answer": None,
                "metadata": {}
            }
        else:
            initial_state = session_state.copy()
        
        initial_state["messages"].append(HumanMessage(content=user_input))
        
        try:
            # 流式执行
            async for event in self.graph.astream(initial_state):
                yield event
                
        except Exception as e:
            print(f"[SmartCarConcierge] 流式执行异常: {e}")
            yield {"error": str(e)}


# ==========================================
# 便捷函数：创建 Agent 实例
# ==========================================
def create_smart_car_concierge() -> SmartCarConciergeAgent:
    """
    工厂函数：创建智能购车管家 Agent
    
    使用示例:
        agent = create_smart_car_concierge()
        result = await agent.chat("20万左右的SUV有哪些推荐")
        print(result["answer"])
    """
    return SmartCarConciergeAgent()


# ==========================================
# 测试代码
# ==========================================
if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        agent = create_smart_car_concierge()
        
        # 测试对话1: 打招呼
        print("\n" + "="*60)
        print("测试1: 打招呼")
        print("="*60)
        result1 = await agent.chat("你好")
        print(f"AI: {result1['answer']}")
        print(f"用户画像: {result1['metadata']['user_profile']}")
        
        # 测试对话2: 咨询车型（携带上次状态）
        print("\n" + "="*60)
        print("测试2: 咨询车型")
        print("="*60)
        result2 = await agent.chat(
            "我预算20万左右，想买辆SUV，有什么推荐吗",
            session_state=result1["state"]
        )
        print(f"AI: {result2['answer']}")
        print(f"用户画像: {result2['metadata']['user_profile']}")
        
        # 测试对话3: 查询具体车型
        print("\n" + "="*60)
        print("测试3: 查询具体车型")
        print("="*60)
        result3 = await agent.chat(
            "比亚迪秦PLUS怎么样",
            session_state=result2["state"]
        )
        print(f"AI: {result3['answer']}")
    
    asyncio.run(test_agent())
