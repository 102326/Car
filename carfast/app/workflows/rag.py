# app/workflows/rag.py
import json
import logging
from typing import AsyncGenerator, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.llm_factory import LLMFactory
from app.services.es_service import EsService

# 配置日志
logger = logging.getLogger(__name__)

# 系统提示词
SYSTEM_PROMPT = """你是一个专业的汽车导购助手 CarFast AI。
你的任务是根据用户的需求和提供的【相关车辆信息】，进行专业的推荐。

请遵守以下规则：
1. 必须基于【相关车辆信息】中的数据进行回答，不要编造参数。
2. 如果车辆信息中没有用户想要的，请礼貌告知，并建议用户调整搜索条件。
3. 输出格式要自然流畅，像专业的销售顾问一样，使用 Markdown 格式。
4. 重点介绍价格、车型、动力和亮点配置。
5. 不要直接列出 JSON 数据，而是将其转化为自然语言描述。

【相关车辆信息】：
{context}
"""


async def chat_stream(query: str, user_id: int = None) -> AsyncGenerator[str, None]:
    """
    RAG 流式对话核心逻辑
    Yields: JSON String (related_cars -> stream_text -> done/error)
    """
    try:
        # -------------------------------------------------------
        # 1. Retrieve (检索): 从 ES 获取真实车辆数据
        # -------------------------------------------------------
        try:
            # 假设 EsService.search 返回 Pydantic 模型或 Dict
            # 限制 Top 3 避免 Context 过大
            search_results = await EsService.search(query, page=1, size=3)
        except Exception as es_err:
            logger.error(f"ES Search Error: {es_err}")
            # 降级处理：给空列表，让 LLM 凭常识回答或道歉
            search_results = {"items": []}

        # 数据清洗：提取 items 并转为 dict 列表
        cars_data: List[Dict[str, Any]] = []

        # 兼容处理 search_results 的不同返回格式 (Dict 或 List)
        raw_items = []
        if isinstance(search_results, dict) and "items" in search_results:
            raw_items = search_results["items"]
        elif isinstance(search_results, list):
            raw_items = search_results

        for item in raw_items:
            if hasattr(item, "model_dump"):
                cars_data.append(item.model_dump())
            elif hasattr(item, "dict"):
                cars_data.append(item.dict())
            else:
                cars_data.append(dict(item))

        # -------------------------------------------------------
        # 2. Yield Cars (事件: 推送车辆卡片)
        # -------------------------------------------------------
        if cars_data:
            yield json.dumps({
                "type": "related_cars",
                "data": cars_data
            }, default=str)  # default=str 处理 datetime 序列化

        # -------------------------------------------------------
        # 3. Augment (增强上下文)
        # -------------------------------------------------------
        context_str = ""
        if cars_data:
            for car in cars_data:
                # 容错获取字段
                name = car.get("name", "未知车型")
                price = car.get("price", "未知")
                desc = f"- 车型: {name}, 指导价: {price}万"
                context_str += desc + "\n"
        else:
            context_str = "（数据库中暂无匹配车辆，请根据通用汽车知识回答，并提示用户我们暂时没有这款车）"

        # -------------------------------------------------------
        # 4. Generate (流式生成)
        # -------------------------------------------------------
        llm = LLMFactory.get_llm(streaming=True)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "{question}")
        ])

        chain = prompt | llm | StrOutputParser()

        # 开始流式输出文本 (事件: stream_text)
        async for chunk in chain.astream({"context": context_str, "question": query}):
            if chunk:
                yield json.dumps({
                    "type": "stream_text",
                    "content": chunk
                })

    except Exception as e:
        logger.error(f"RAG Workflow Error: {e}", exc_info=True)
        yield json.dumps({
            "type": "error",
            "message": "AI 服务暂时繁忙，请稍后再试。"
        })
    finally:
        # -------------------------------------------------------
        # 5. Done (事件: 结束信号)
        # -------------------------------------------------------
        # 无论成功失败，必须发送 done，否则前端 loading 会一直转
        yield json.dumps({"type": "done"})