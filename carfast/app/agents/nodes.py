# app/agents/nodes.py
"""
LangGraph 节点实现
"""
import json
import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.model_factory import ModelFactory, ModelType
from app.agents.state import AgentState, UserProfile
from app.agents.prompts import (
    INTENT_ROUTER_PROMPT,
    RAG_GENERATION_PROMPT,
    USER_PROFILE_EXTRACTION_PROMPT
)

logger = logging.getLogger(__name__)


# ==========================================
# 1. 意图识别节点 (Intent Router)
# ==========================================
async def intent_router_node(state: AgentState) -> Dict[str, Any]:
    """
    分析用户最新消息，判断路由方向
    
    返回:
        next_step: "rag" | "enrichment" | "trade" | "chat" | "end"
    """
    from app.core.logging_config import StructuredLogger, log_performance
    import time
    
    start_time = time.time()
    logger_struct = StructuredLogger("agent.intent_router")
    
    messages = state["messages"]
    user_profile = state.get("user_profile", {})
    
    # 获取最新的用户消息
    user_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    
    logger_struct.log_event("intent_analysis_start", {
        "user_message": user_message[:100],  # 截取前100字符
        "user_profile": user_profile
    })
    
    # 获取最近3轮对话历史
    recent_history = messages[-6:] if len(messages) >= 6 else messages
    history_text = "\n".join([
        f"{'用户' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" 
        for m in recent_history
    ])
    
    # 使用"大脑"模型（qwen2.5-coder:14b）进行意图识别
    llm = ModelFactory.get_brain_model(temperature=0.1)
    
    prompt = ChatPromptTemplate.from_template(INTENT_ROUTER_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    try:
        result = await chain.ainvoke({
            "user_message": user_message,
            "user_profile": json.dumps(user_profile, ensure_ascii=False),
            "recent_history": history_text
        })
        
        # 解析JSON结果（处理 Markdown 代码块）
        from app.utils.json_extractor import safe_json_loads
        intent_data = safe_json_loads(result, default={"intent": "rag", "confidence": 0.5, "reasoning": "JSON解析失败，使用默认路由"})
        next_step = intent_data.get("intent", "rag")
        
        # 更新用户画像（如果提取到新实体）
        extracted_entities = intent_data.get("extracted_entities", {})
        updated_profile = _update_user_profile(user_profile, extracted_entities)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"[Intent Router] 识别意图: {next_step}, 置信度: {intent_data.get('confidence', 0)}")
        logger.info(f"[Intent Router] 推理: {intent_data.get('reasoning', '')}")
        
        # 记录结构化日志
        logger_struct.log_event("intent_analysis_complete", {
            "next_step": next_step,
            "confidence": intent_data.get("confidence", 0),
            "reasoning": intent_data.get("reasoning", ""),
            "extracted_entities": extracted_entities,
            "elapsed_ms": elapsed_ms
        })
        
        return {
            "next_step": next_step,
            "user_profile": updated_profile,
            "metadata": {
                "intent_confidence": intent_data.get("confidence", 0),
                "intent_reasoning": intent_data.get("reasoning", ""),
                "elapsed_ms": elapsed_ms
            }
        }
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        logger.error(f"[Intent Router] 解析失败，默认路由到RAG: {e}")
        
        logger_struct.log_event("intent_analysis_failed", {
            "error": str(e),
            "fallback_step": "rag",
            "elapsed_ms": elapsed_ms
        }, level="ERROR")
        
        return {"next_step": "rag"}


# ==========================================
# 2. RAG 节点 (Retrieval-Augmented Generation)
# ==========================================
async def rag_node(state: AgentState) -> Dict[str, Any]:
    """
    调用混合检索（ES + Milvus），生成基于Context的回答
    """
    from app.core.logging_config import StructuredLogger
    import time
    
    start_time = time.time()
    logger_struct = StructuredLogger("agent.rag")
    
    messages = state["messages"]
    user_profile = state.get("user_profile", {})
    
    # 获取用户问题
    user_question = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    # ==========================================
    # 接入混合检索服务（ES + Milvus）
    # ==========================================
    try:
        from app.services.hybrid_search_service import hybrid_search
        
        # 执行混合检索
        search_results = await hybrid_search(user_question, top_k=5)
        
        if search_results:
            # 构造 Context
            context_parts = []
            for idx, result in enumerate(search_results, 1):
                context_parts.append(f"""
【车型 {idx}】{result.name}
- 品牌: {result.brand_name}
- 车系: {result.series_name}
- 价格: {result.price}万
- 能源类型: {result.energy_type}
- 级别: {result.series_level}
- 标签: {result.tags_text or '暂无'}
- 相关度得分: {result.score:.2f}
""")
            context = "\n".join(context_parts)
            
            logger.info(f"[RAG Node] 混合检索找到 {len(search_results)} 条结果")
            
            # 记录检索日志
            logger_struct.log_search(
                search_type="hybrid",
                query=user_question[:100],
                results_count=len(search_results),
                elapsed_ms=int((time.time() - start_time) * 1000)
            )
        else:
            # 检索为空，使用模拟数据
            logger.warning(f"[RAG Node] 混合检索无结果，使用模拟数据")
            context = _mock_rag_retrieve(user_question, user_profile)
    
    except Exception as e:
        logger.error(f"[RAG Node] 混合检索失败，使用模拟数据: {e}")
        context = _mock_rag_retrieve(user_question, user_profile)
    
    # 如果检索结果为空，路由到数据补充节点
    if not context or len(context) < 50:
        print("[RAG Node] 检索结果为空，路由到数据补充节点")
        return {
            "rag_context": context,
            "next_step": "enrichment"
        }
    
    # 使用"快嘴"模型（qwen2.5:7b）生成回答（基于检索结果，任务简单）
    llm = ModelFactory.get_quick_model(temperature=0.7)
    prompt = ChatPromptTemplate.from_template(RAG_GENERATION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    answer = await chain.ainvoke({
        "question": user_question,
        "context": context,
        "budget": f"{user_profile.get('budget_min', '未知')}-{user_profile.get('budget_max', '未知')}万",
        "city": user_profile.get("city", "未知"),
        "preferences": json.dumps(user_profile.get("preferences", {}), ensure_ascii=False)
    })
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    logger.info(f"[RAG Node] 生成回答长度: {len(answer)} 字符")
    
    # 记录 RAG 完成日志
    logger_struct.log_event("rag_complete", {
        "answer_length": len(answer),
        "context_length": len(context),
        "elapsed_ms": elapsed_ms
    })
    
    return {
        "rag_context": context,
        "final_answer": answer,
        "next_step": "end",
        "metadata": {"elapsed_ms": elapsed_ms}
    }


# ==========================================
# 3. 数据补充节点 (Data Enrichment)
# ==========================================
async def data_enrichment_node(state: AgentState) -> Dict[str, Any]:
    """
    调用数据补充子Agent，获取实时数据
    """
    messages = state["messages"]
    user_profile = state.get("user_profile", {})
    
    # 获取用户问题
    user_question = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    # ==========================================
    # 调用数据补充 Graph Agent
    # ==========================================
    try:
        from app.agents.enrichment_graph import DataEnrichmentAgent
        
        # 提取车系名称（简单示例）
        car_series_name = _extract_car_series_from_question(user_question)
        
        if not car_series_name:
            # 如果无法提取车系名称，使用模拟数据
            enrichment_result = _mock_data_enrichment(user_question, user_profile)
        else:
            # 调用数据补充 Agent
            enrichment_agent = DataEnrichmentAgent()
            result = await enrichment_agent.enrich(
                car_series_name=car_series_name,
                force_refresh=False,
                user_city=user_profile.get("city")
            )
            
            # 转换为字典格式
            enrichment_result = {
                "success": result.success,
                "data": result.data or {},
                "message": result.message,
                "update_time": result.update_time
            }
            
            print(f"[DataEnrichment] 数据补充完成: {result.source}")
    
    except Exception as e:
        print(f"[DataEnrichment] 调用失败，使用模拟数据: {e}")
        enrichment_result = _mock_data_enrichment(user_question, user_profile)
    
    # 使用"快嘴"模型生成回答
    llm = ModelFactory.get_quick_model(temperature=0.7)
    
    enriched_context = f"""
我刚刚为您更新了最新数据（更新时间: {enrichment_result.get('update_time', '未知')}）：

{json.dumps(enrichment_result.get('data', {}), ensure_ascii=False, indent=2)}
"""
    
    prompt = ChatPromptTemplate.from_template(RAG_GENERATION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    answer = await chain.ainvoke({
        "question": user_question,
        "context": enriched_context,
        "budget": f"{user_profile.get('budget_min', '未知')}-{user_profile.get('budget_max', '未知')}万",
        "city": user_profile.get("city", "未知"),
        "preferences": json.dumps(user_profile.get("preferences", {}), ensure_ascii=False)
    })
    
    # 在答案前加上明确的数据更新提示
    final_answer = f"✅ 我刚刚为您更新了这款车的最新数据...\n\n{answer}"
    
    print(f"[Data Enrichment] 数据补充完成")
    
    return {
        "enrichment_result": enrichment_result,
        "final_answer": final_answer,
        "next_step": "end"
    }


# ==========================================
# 4. 交易节点 (Trade)
# ==========================================
async def trade_node(state: AgentState) -> Dict[str, Any]:
    """
    处理交易相关请求（订金、试驾、二手车估价）
    """
    messages = state["messages"]
    user_profile = state.get("user_profile", {})
    
    # 获取用户问题
    user_question = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    # 调用交易服务
    try:
        from app.services.trade_service import TradeService
        trade_info = await TradeService.handle_request(
            query=user_question,
            user_id=state.get("metadata", {}).get("user_id"),  # 从 state metadata 中获取
            user_city=user_profile.get("city")
        )
    except Exception as e:
        logger.error(f"[Trade Node] 交易服务调用失败: {e}")
        trade_info = _mock_trade_service(user_question, user_profile)
    
    # 使用"快嘴"模型生成回答
    llm = ModelFactory.get_quick_model(temperature=0.7)
    
    trade_prompt = f"""
你是易车购车管家，用户咨询交易相关问题。

用户问题: {user_question}

交易信息:
{json.dumps(trade_info, ensure_ascii=False, indent=2)}

请生成友好的回复，如果涉及金钱交易，务必提醒用户：
"温馨提示：支付前请仔细阅读协议条款，如有疑问可联系客服。"

回复:
"""
    
    answer = await llm.ainvoke(trade_prompt)
    final_answer = answer.content if hasattr(answer, 'content') else str(answer)
    
    print(f"[Trade Node] 交易请求处理完成")
    
    return {
        "trade_info": trade_info,
        "final_answer": final_answer,
        "next_step": "end"
    }


# ==========================================
# 5. 闲聊节点 (Chat)
# ==========================================
async def chat_node(state: AgentState) -> Dict[str, Any]:
    """
    处理闲聊、打招呼等非业务对话
    """
    messages = state["messages"]
    
    # 获取用户消息
    user_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    
    # 简单的规则匹配
    greetings = ["你好", "您好", "hi", "hello", "早上好", "晚上好"]
    thanks = ["谢谢", "感谢", "多谢", "thanks", "thank you"]
    
    if any(g in user_message.lower() for g in greetings):
        answer = "您好！我是易车智能购车管家，很高兴为您服务。您可以问我关于汽车的任何问题，比如推荐车型、查询价格、对比参数等。请问有什么可以帮您的吗？😊"
    elif any(t in user_message.lower() for t in thanks):
        answer = "不客气！如果还有其他问题，随时问我哦。祝您早日找到心仪的爱车！🚗"
    else:
        # 使用"快嘴"模型生成闲聊回复（速度快）
        llm = ModelFactory.get_quick_model(temperature=0.9)
        chat_prompt = f"""
你是易车购车管家，用户发来闲聊消息: "{user_message}"

请用友好、自然的方式回复，适当引导用户提出购车相关问题。
回复要简短（不超过50字），语气轻松。

回复:
"""
        answer_msg = await llm.ainvoke(chat_prompt)
        answer = answer_msg.content if hasattr(answer_msg, 'content') else str(answer_msg)
    
    print(f"[Chat Node] 闲聊回复")
    
    return {
        "final_answer": answer,
        "next_step": "end"
    }


# ==========================================
# 辅助函数
# ==========================================
def _update_user_profile(current_profile: UserProfile, extracted_entities: Dict[str, Any]) -> UserProfile:
    """更新用户画像"""
    updated = current_profile.copy()
    
    # 更新预算
    if "budget" in extracted_entities and isinstance(extracted_entities["budget"], list):
        updated["budget_min"] = extracted_entities["budget"][0]
        updated["budget_max"] = extracted_entities["budget"][1]
    
    # 更新城市
    if "city" in extracted_entities:
        updated["city"] = extracted_entities["city"]
    
    # 更新偏好
    preferences = updated.get("preferences", {})
    for key in ["car_brand", "car_series", "energy_type", "level"]:
        if key in extracted_entities:
            preferences[key] = extracted_entities[key]
    updated["preferences"] = preferences
    
    return updated


def _mock_rag_retrieve(question: str, user_profile: UserProfile) -> str:
    """模拟RAG检索（开发阶段）"""
    # 简单的关键词匹配
    if "秦PLUS" in question or "秦plus" in question.lower():
        return """
【比亚迪秦PLUS DM-i】
- 2026款 120km 冠军版: 指导价 11.98万，实际优惠后约 10.98万
- 2026款 120km 尊贵型: 指导价 13.98万
- 能源类型: 插电式混合动力
- NEDC纯电续航: 120km
- 综合油耗: 3.8L/100km
- 车身级别: 紧凑型车
- 座位数: 5座
- 补贴政策: 部分城市可享受新能源补贴和免购置税
"""
    elif "SUV" in question or "suv" in question.lower():
        return """
【20万左右SUV推荐】
1. 比亚迪宋PLUS DM-i: 15.98-21.98万，插电混动，续航110km
2. 理想L6: 24.98万起，增程式，续航210km
3. 本田CR-V: 18.59-26.39万，燃油/混动可选
4. 大众途观L: 21.58-28.58万，燃油，空间大
"""
    else:
        return ""  # 触发enrichment


def _mock_data_enrichment(question: str, user_profile: UserProfile) -> Dict[str, Any]:
    """模拟数据补充服务"""
    return {
        "success": True,
        "data": {
            "car_series": "比亚迪秦PLUS",
            "models": [
                {
                    "name": "2026款 DM-i 120km 冠军版",
                    "price_guidance": 11.98,
                    "price_real": 10.98,
                    "subsidy": 1.5,
                    "dealer_discount": 0.5
                }
            ],
            "local_policy": f"{user_profile.get('city', '本地')}地区可享受新能源补贴1.5万元"
        },
        "update_time": "2026-01-15 10:30:00"
    }


def _mock_trade_service(question: str, user_profile: UserProfile) -> Dict[str, Any]:
    """模拟交易服务"""
    if "试驾" in question:
        return {
            "type": "test_drive",
            "message": "已为您推荐附近的经销商",
            "dealers": [
                {"name": "XX比亚迪4S店", "phone": "010-12345678", "address": "北京市朝阳区XX路XX号"}
            ]
        }
    elif "估价" in question or "置换" in question:
        return {
            "type": "trade_in",
            "message": "二手车估价需要提供车辆详细信息",
            "required_info": ["品牌", "车系", "年款", "里程", "车况"]
        }
    else:
        return {
            "type": "order",
            "message": "订金支付功能开发中，敬请期待"
        }


def _extract_car_series_from_question(question: str) -> str:
    """
    从用户问题中提取车系名称
    
    使用正则表达式 + 关键词库匹配
    """
    import re
    
    # 已知车系库（按长度排序，优先匹配长的）
    known_series = [
        "秦PLUS", "秦Plus", "秦plus", "秦",
        "汉", "唐", "宋PLUS", "海豹", "海鸥", "元PLUS",
        "Model 3", "Model Y", "Model S", "Model X",
        "理想L6", "理想L7", "理想L8", "理想L9", "理想ONE",
        "小鹏P7", "小鹏G9", "小鹏G6", "小鹏P5",
        "蔚来ET5", "蔚来ES6", "蔚来ET7", "蔚来ES8",
        "奥迪A4L", "奥迪A6L", "奥迪Q5L", "奥迪Q7",
        "宝马3系", "宝马5系", "宝马X3", "宝马X5",
        "奔驰C级", "奔驰E级", "奔驰GLC", "奔驰GLE",
        "本田CR-V", "本田雅阁", "本田思域", "本田飞度",
        "大众途观L", "大众帕萨特", "大众高尔夫", "大众朗逸",
        "丰田卡罗拉", "丰田凯美瑞", "丰田RAV4", "丰田汉兰达"
    ]
    known_series.sort(key=len, reverse=True)
    
    question_lower = question.lower()
    
    # 精确匹配
    for series in known_series:
        if series.lower() in question_lower:
            return series
    
    # 正则模式匹配（如 "L6"、"ES6" 等）
    patterns = [
        r'[A-Z]+\d+[A-Z]*',  # 匹配 A4L, ES6, L7 等
        r'[\u4e00-\u9fff]+(?:PLUS|Plus|plus)?',  # 匹配中文+PLUS
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, question)
        if matches:
            # 返回最长的匹配
            return max(matches, key=len)
    
    return ""
