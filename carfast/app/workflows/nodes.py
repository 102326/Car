# app/workflows/nodes.py
import logging
from typing import Any, Dict, Optional, List

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from app.workflows.state import AgentState
from app.utils.search_tool import VehicleSearchTool
from app.utils.llm_factory import LLMFactory
from app.services.memory_service import get_user_profile_summary, update_user_profile_partial
from app.schemas.profile import ProfileUpdateResult
from app.utils.decorators import async_time_it

logger = logging.getLogger(__name__)

# ============================================================================
# Pydantic Schemas (新增：用于强制大模型结构化输出)
# ============================================================================

class SearchParamsSchema(BaseModel):
    query: Optional[str] = Field(None, description="用户描述的车辆特征或需求")
    min_price: Optional[int] = Field(None, description="最低预算，单位万元")
    max_price: Optional[int] = Field(None, description="最高预算，单位万元")
    brand: Optional[str] = Field(None, description="品牌名称，如 '宝马', '奔驰'")
    tags: Optional[List[str]] = Field(None, description="车辆标签列表，如 ['SUV', '省油']")

class CalculateParamsSchema(BaseModel):
    total_price: Optional[float] = Field(None, description="车辆总价（单位：万元）。必须提取，如果没提则为空")
    down_payment_rate: Optional[float] = Field(None, description="首付比例（如 0.3 表示 30%）。如果没提，请不要瞎编")
    loan_term: Optional[int] = Field(None, description="贷款期数（如 12, 24, 36 月）。如果没提，请不要瞎编")
    annual_rate: Optional[float] = Field(None, description="年化利率（如 0.045 表示 4.5%）。如果没提，请不要瞎编")

class IntentClassificationSchema(BaseModel):
    intent: str = Field(..., description="用户意图，必须是以下三个之一: 'search', 'chat', 'calculate'")
    search_params: Optional[SearchParamsSchema] = Field(None, description="当 intent 为 'search' 时提取的参数")
    calculate_params: Optional[CalculateParamsSchema] = Field(None, description="当 intent 为 'calculate' 时提取的参数")


# ============================================================================
# System Prompts (精简版：去掉了所有关于 JSON 格式的硬性要求)
# ============================================================================

PROFILE_EXTRACTION_PROMPT = """你是一个专业的购车顾问助手，专注于从对话中提取用户的购车偏好。

## 任务
分析用户的最新消息，判断用户是否表达了**修改**购车偏好（品牌、预算、标签）的意图。
- 仅当用户明确表达了新的偏好或修改原有偏好时，才进行提取。
- 如果只是闲聊或询问车辆信息但未表达偏好变更，has_changed 设为 false。
"""

INTENT_SYSTEM_PROMPT = """你是一个汽车销售助手的意图分析器。

## 任务
分析用户的最新消息，判断其意图并提取相关参数。

## 意图分类
1. **search** - 用户想查找、比较或获取车辆推荐 (关键词: 找车、推荐、比价、预算等)
2. **chat** - 普通闲聊或与车辆无关的问题 (关键词: 你好、谢谢、帮助等)
3. **calculate** - 用户想计算费用 (关键词: 分期、月供、首付、保险等)

如果用户没有明确指定某些搜索参数，你可以参考下方提供的【用户画像】作为默认值。
"""

# ============================================================================
# Node Functions
# ============================================================================

@async_time_it
async def extract_profile(state: AgentState) -> Dict[str, Any]:
    logger.info("[Node: extract_profile] Checking for profile updates...")
    user_id = state.get("user_id")
    messages = state.get("messages", [])
    
    if not user_id or not messages or not isinstance(messages[-1], HumanMessage):
        return {}
        
    try:
        llm = LLMFactory.get_llm(temperature=0.0)
        # 💡 核心魔法：让 LLM 直接输出 ProfileUpdateResult 对象！
        structured_llm = llm.with_structured_output(ProfileUpdateResult, method="function_calling")
        
        prompt = PromptTemplate.from_template(
            PROFILE_EXTRACTION_PROMPT + "\n用户最新消息: {message}"
        )
        chain = prompt | structured_llm
        
        # 返回的直接是 Pydantic 对象，无需再做 JSON 解析！
        result: ProfileUpdateResult = await chain.ainvoke({"message": messages[-1].content})
        
        if result.has_changed:
            logger.info(f"[Node: extract_profile] Extracted changes: {result.model_dump()}")
            await update_user_profile_partial(str(user_id), result)
            
    except Exception as e:
        logger.error(f"[Node: extract_profile] Error: {e}")
        
    return {}


@async_time_it
async def identify_intent(state: AgentState) -> Dict[str, Any]:
    logger.info("[Node: identify_intent] Starting intent classification...")
    default_result = {"intent": "chat", "search_params": None, "step_count": 1}
    
    try:
        messages = state.get("messages", [])
        if not messages:
            return default_result
            
        user_id = state.get("user_id")
        user_profile_section = ""
        if user_id:
            try:
                profile_summary = await get_user_profile_summary(user_id)
                if profile_summary and profile_summary != "暂无用户偏好记录":
                    user_profile_section = f"\n\n## 用户画像\n该用户的历史偏好记录如下：\n{profile_summary}"
            except Exception:
                pass

        llm = LLMFactory.get_llm(temperature=0.1, streaming=False)
        # 💡 核心魔法：绑定我们刚才定义的 IntentClassificationSchema
        structured_llm = llm.with_structured_output(IntentClassificationSchema, method="function_calling")
        
        system_prompt = INTENT_SYSTEM_PROMPT + user_profile_section
        llm_messages = [SystemMessage(content=system_prompt)]
        
        for msg in messages[-5:]:
            llm_messages.append(msg)
            
        # 返回的是 IntentClassificationSchema 对象
        result: IntentClassificationSchema = await structured_llm.ainvoke(llm_messages)

        # 验证意图合法性
        intent = result.intent if result.intent in ("search", "chat", "calculate") else "chat"
        search_params = result.search_params.model_dump(
            exclude_none=True) if result.search_params and intent == "search" else None

        # 🌟 新增：解析计算参数
        calculate_params = result.calculate_params.model_dump(
            exclude_none=True) if result.calculate_params and intent == "calculate" else None

        logger.info(f"[Node: identify_intent] Classified intent: {intent}, Params: {search_params or calculate_params}")

        return {
            "intent": intent,
            "search_params": search_params,
            "calculate_params": calculate_params,  # 🌟 新增这行
            "step_count": 1
        }
        
    except Exception as e:
        logger.error(f"[Node: identify_intent] Error: {e}", exc_info=True)
        return default_result


@async_time_it
async def execute_search(state: AgentState) -> Dict[str, Any]:
    logger.info("[Node: execute_search] Starting vehicle search...")
    try:
        search_params = state.get("search_params") or {}
        tool = VehicleSearchTool()
        
        result = await tool._arun(
            query=search_params.get("query"),
            min_price=search_params.get("min_price"),
            max_price=search_params.get("max_price"),
            brand=search_params.get("brand"),
            tags=search_params.get("tags"),
            sort_strategy=search_params.get("sort_strategy", "default")
        )
        
        return {"tool_output": result, "step_count": 1}
        
    except Exception as e:
        logger.error(f"[Node: execute_search] Error: {e}", exc_info=True)
        return {"tool_output": f"[搜索执行失败] {str(e)}", "step_count": 1}


@async_time_it
async def calculate_executor(state: AgentState) -> Dict[str, Any]:
    """执行真实的金融车贷计算（等额本息）"""
    logger.info("[Node: calculate_executor] Starting financial calculation...")
    try:
        params = state.get("calculate_params") or {}
        total_price = params.get("total_price")

        # 兜底：如果用户没提总价，无法计算
        if not total_price:
            return {"tool_output": "[系统提示] 无法计算，因为用户未提供车辆总价。请询问用户想要计算的具体车价。"}

        # 设置默认值（业界常规标准：首付3成，分36期，年化4.5%）
        down_payment_rate = params.get("down_payment_rate") or 0.3
        loan_term = params.get("loan_term") or 36
        annual_rate = params.get("annual_rate") or 0.045

        # 数学计算：等额本息公式
        principal = total_price * 10000 * (1 - down_payment_rate)  # 贷款本金(元)
        monthly_rate = annual_rate / 12  # 月利率

        if monthly_rate > 0:
            monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** loan_term) / (
                        (1 + monthly_rate) ** loan_term - 1)
        else:
            monthly_payment = principal / loan_term

        total_interest = monthly_payment * loan_term - principal

        # 组装精确的格式化输出结果交给大模型
        result_str = (
            f"【后台车贷系统计算结果 (等额本息)】\n"
            f"- 车辆总价：{total_price} 万元\n"
            f"- 首付比例：{down_payment_rate * 100}% \n"
            f"- 首付金额：{total_price * down_payment_rate:.2f} 万元\n"
            f"- 贷款本金：{principal / 10000:.2f} 万元\n"
            f"- 贷款期限：{loan_term} 期 (月)\n"
            f"- 年化利率：{annual_rate * 100}%\n"
            f"- 每月月供：{monthly_payment:.2f} 元\n"
            f"- 总利息：{total_interest:.2f} 元\n\n"
            f"系统要求：请以专业的销售口吻将上述计算结果告知用户，不需要解释数学公式，只需报出数据，"
            f"并友好地提醒用户：具体金融政策与费率请以门店实际审批为准。"
        )
        return {"tool_output": result_str, "step_count": 1}

    except Exception as e:
        logger.error(f"[Node: calculate_executor] Error: {e}", exc_info=True)
        return {"tool_output": f"[计算执行失败] 无法完成计算，请稍后重试。({str(e)})", "step_count": 1}