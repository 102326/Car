# app/workflows/nodes.py
import logging
from typing import Any, Dict, Optional, List, Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from app.workflows.state import AgentState
from app.utils.search_tool import VehicleSearchTool
from app.utils.llm_factory import LLMFactory
from app.services.memory_service import get_user_profile_summary, update_user_profile_partial
from app.schemas.profile import ProfileUpdateResult
from app.utils.decorators import async_time_it
import json
import os
from app.services.mcp_client import CarFastMCPClient

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

class CriticSchema(BaseModel):
    decision: Literal["pass", "reject"] = Field(description="审核结果：符合现实商业逻辑为 pass，离谱或不切实际为 reject")
    reason: Optional[str] = Field(None, description="如果 reject，请给出具体的拒绝理由（给销售看的提示）")

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
        structured_llm = llm.with_structured_output(ProfileUpdateResult, method="function_calling")

        prompt = PromptTemplate.from_template(
            PROFILE_EXTRACTION_PROMPT + "\n用户最新消息: {message}"
        )
        chain = prompt | structured_llm

        result: ProfileUpdateResult = await chain.ainvoke({"message": messages[-1].content})

        if result.has_changed:
            logger.info(f"[Node: extract_profile] Extracted changes: {result.model_dump()}")
            # 1. 持久化到数据库
            await update_user_profile_partial(str(user_id), result)

            # 🌟 2. 核心补丁：按照新的结构，把数据送给 LangGraph 的神级 Reducer！
            profile_update = {}
            if result.tags_to_add or result.tags_to_remove:
                profile_update["preference_tags"] = {
                    "_add": result.tags_to_add or [],
                    "_remove": result.tags_to_remove or []
                }
            if result.new_budget_min is not None:
                profile_update["budget_min"] = result.new_budget_min
            if result.new_budget_max is not None:
                profile_update["budget_max"] = result.new_budget_max
            if result.new_brand is not None:
                profile_update["preference_brand"] = result.new_brand

            return {"user_profile": profile_update, "step_count": 1}

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
    logger.info("[Node: calculate_executor] 正在通过 MCP 协议调用外部金融引擎...")

    intent = state.get("intent")
    # 假设你之前已经把参数提取到这儿了，或者写死几个参数测试
    params = state.get("calculate_params", {})

    # 获取测试参数（你可以根据实际情况从 params 里取，这里为了演示 MCP 连通性给个默认值）
    principal = params.get("principal", 200000)
    months = params.get("months", 36)
    annual_rate = params.get("annual_rate", 0.05)

    # 🌟 核心重构：MCP 跨进程远程调用 🌟
    # 找到 finance_server.py 的绝对或相对路径
    server_path = os.path.join(os.getcwd(), "mcp_servers", "finance_server.py")

    mcp_client = CarFastMCPClient(server_path)
    tool_output_str = ""

    try:
        # 1. 连接 MCP Server
        await mcp_client.connect()

        # 2. 发起工具调用！这就相当于在进行一次本机的微服务 RPC 通信
        result_str = await mcp_client.call_tool(
            name="calculate_car_loan",
            arguments={
                "principal": principal,
                "months": months,
                "annual_rate": annual_rate
            }
        )

        # 解析返回的 JSON 字符串
        result_json = json.loads(result_str)

        # 组装给大模型看的最终上下文
        tool_output_str = (
            f"✅ [MCP 远程调用成功]\n"
            f"- 贷款本金: {principal} 元\n"
            f"- 分期期数: {months} 个月\n"
            f"- 年化利率: {annual_rate * 100}%\n"
            f"💰 每月等额本息月供: **{result_json['monthly_payment']} 元**\n"
            f"📊 总利息: {result_json['total_interest']} 元\n"
        )

    except Exception as e:
        logger.error(f"[MCP 调用异常] {e}", exc_info=True)
        tool_output_str = f"❌ [金融服务引擎调用失败]: {str(e)}"

    finally:
        # 3. 务必断开连接，释放子进程资源
        await mcp_client.close()

    # 将外部微服务的计算结果，塞回 LangGraph 的状态中
    return {"tool_output": tool_output_str, "step_count": 1}


@async_time_it
async def calculate_critic(state: AgentState) -> Dict[str, Any]:
    """反思节点 (Critic)：双引擎金融风控 (硬规则 + LLM 语义审核)"""
    logger.info("[Node: calculate_critic] Auditing financial calculation...")

    tool_output = state.get("tool_output", "")
    params = state.get("calculate_params") or {}

    # 如果前面计算已经报错了，直接放行，让生成节点去处理异常
    if "[计算执行失败]" in tool_output or "[系统提示]" in tool_output:
        return {"critic_decision": "pass", "step_count": 1}

    # ==========================================
    # 🌟 第一重保险：Python 确定性硬规则拦截 (Deterministic)
    # ==========================================
    loan_term = params.get("loan_term")
    down_payment_rate = params.get("down_payment_rate")

    if loan_term and (int(loan_term) > 120 or int(loan_term) < 12):
        reason = f"贷款期数 {loan_term} 个月不符合现实业务标准 (需在12到120个月之间)。"
        logger.warning(f"[Critic] 硬规则拦截: {reason}")
        return {"critic_decision": "reject", "critic_reason": reason, "step_count": 1}

    if down_payment_rate is not None and float(down_payment_rate) < 0.15:
        reason = f"首付比例 {float(down_payment_rate) * 100}% 过低，金融机构最低要求通常为15%。"
        logger.warning(f"[Critic] 硬规则拦截: {reason}")
        return {"critic_decision": "reject", "critic_reason": reason, "step_count": 1}

    # ==========================================
    # 🌟 第二重保险：LLM 语义与常识拦截 (Probabilistic)
    # ==========================================
    try:
        llm = LLMFactory.get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(CriticSchema, method="function_calling")

        prompt = f"""你是一个严谨的汽车金融风控审核员。
请审查以下车贷计算参数和结果是否符合现实商业逻辑。

【待审核数据】：
用户提供的原始参数：{params}
后台计算出的结果：{tool_output}

如果不符合常识（例如年化利率低得离谱且无免息政策），请坚决输出 reject，并给出具体的理由。如果符合，输出 pass。"""

        result: CriticSchema = await structured_llm.ainvoke([HumanMessage(content=prompt)])

        if result.decision == "reject":
            logger.warning(f"[Critic] LLM 审核拦截: {result.reason}")
            return {"critic_decision": "reject", "critic_reason": result.reason, "step_count": 1}

        logger.info("[Critic] 审核通过，参数合理")
        return {"critic_decision": "pass", "step_count": 1}

    except Exception as e:
        logger.error(f"[Node: calculate_critic] Critic error: {e}", exc_info=True)
        # 降级策略：LLM审核器挂了，但硬规则通过了，予以放行
        return {"critic_decision": "pass", "step_count": 1}