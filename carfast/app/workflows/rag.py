# app/workflows/rag.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.llm_factory import LLMFactory
# from app.services.vector_db import VectorDBService # 新项目需要把向量库服务也搬过来

class RAGState(TypedDict):
    question: str
    context: str
    answer: str

async def retrieve_node(state: RAGState):
    # 这里接入新项目的向量搜索逻辑
    # results = await VectorDBService.search(...)
    context = "模拟检索到的上下文..."
    return {"context": context}

async def generate_node(state: RAGState):
    llm = LLMFactory.get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的汽车智能客服助手（CarFast AI）。请根据提供的上下文信息，礼貌、准确地回答用户的问题。如果上下文中没有相关信息，请基于你的专业知识回答，并注明'根据现有知识库补充'。"),
        ("user", "上下文信息：{context}\n\n用户问题：{question}")
    ])
    chain = prompt | llm | StrOutputParser()
    answer = await chain.ainvoke({"question": state["question"], "context": state["context"]})
    return {"answer": answer}

def build_rag_graph():
    workflow = StateGraph(RAGState)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile()

rag_app = build_rag_graph()