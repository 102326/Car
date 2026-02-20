# app/workflows/rag.py
import json
import logging
from typing import AsyncGenerator, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus

from app.utils.llm_factory import LLMFactory
from app.services.es_service import CarESService
from app.schemas.search import SearchParams
from app.config import settings

logger = logging.getLogger(__name__)

# 全局初始化 Embedding 和 Milvus 检索器 (步骤 8)
try:
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
    milvus_store = Milvus(
        embedding_function=embeddings,
        collection_name=settings.MILVUS_COLLECTION_KNOWLEDGE,
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT}
    )
    # 步骤 9, 10: 设置 Top-K 和 距离阈值
    knowledge_retriever = milvus_store.as_retriever(search_kwargs={"k": 3})
except Exception as e:
    logger.error(f"Milvus 初始化失败: {e}")
    knowledge_retriever = None

# 修改系统提示词以支持多源知识 (步骤 11)
SYSTEM_PROMPT = """你是一个专业的汽车导购助手 CarFast AI。
你的任务是根据用户的需求和提供的【相关车辆库存】及【行业知识参考】，进行专业的推荐和解答。

请遵守以下规则：
1. 必须基于提供的上下文进行回答，不要编造参数和政策。
2. 如果库存中没有用户想要的，请礼貌告知，并建议用户调整搜索条件。
3. 输出格式要自然流畅，像专业的销售顾问一样，使用 Markdown 格式。
4. 结合【行业知识参考】（如补贴、评测）为用户提供附加价值。

【相关车辆库存】：
{car_context}

【行业知识参考】：
{knowledge_context}
"""

async def chat_stream(query: str, user_id: int = None) -> AsyncGenerator[str, None]:
    try:
        # -------------------------------------------------------
        # 1. 结构化检索: 从 ES 获取真实车辆数据
        # -------------------------------------------------------
        try:
            params = SearchParams(q=query, page=1, size=3)
            search_results = await CarESService.search_cars_pro(params)
        except Exception as es_err:
            logger.error(f"ES Search Error: {es_err}")
            search_results = {"list": []}

        cars_data = [
            item.model_dump() if hasattr(item, "model_dump") else (item.dict() if hasattr(item, "dict") else dict(item))
            for item in search_results.get("list", search_results) if isinstance(search_results, (dict, list))
        ]

        if cars_data:
            yield json.dumps({"type": "related_cars", "data": cars_data}, default=str)

        car_context_str = "\n".join([f"- 车型: {c.get('name')}, 指导价: {c.get('price')}万" for c in cars_data]) or "暂无匹配车辆库存。"

        # -------------------------------------------------------
        # 2. 非结构化检索: 从 Milvus 获取外部知识 (步骤 9)
        # -------------------------------------------------------
        knowledge_context_str = "无相关附加知识。"
        if knowledge_retriever:
            try:
                # 异步调用 retriever
                knowledge_docs = await knowledge_retriever.ainvoke(query)
                if knowledge_docs:
                    knowledge_context_str = "\n".join([f"- {doc.page_content}" for doc in knowledge_docs])
            except Exception as v_err:
                logger.error(f"Milvus Search Error: {v_err}")

        # -------------------------------------------------------
        # 3. 生成回答 (步骤 12, 13)
        # -------------------------------------------------------
        llm = LLMFactory.get_llm(streaming=True)
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "{question}")
        ])

        chain = prompt | llm | StrOutputParser()

        async for chunk in chain.astream({
            "car_context": car_context_str,
            "knowledge_context": knowledge_context_str,
            "question": query
        }):
            if chunk:
                yield json.dumps({"type": "stream_text", "content": chunk})

    except Exception as e:
        logger.error(f"RAG Workflow Error: {e}", exc_info=True)
        yield json.dumps({"type": "error", "message": "AI 服务暂时繁忙，请稍后再试。"})
    finally:
        yield json.dumps({"type": "done"})