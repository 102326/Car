"""
LangGraph Core Node Functions for CarFast Agent.

This module implements the core async node functions that form the
reasoning graph of the car shopping assistant agent.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from app.workflows.state import AgentState
from app.utils.search_tool import VehicleSearchTool
from app.utils.llm_factory import LLMFactory
from app.services.memory_service import get_user_profile_summary, update_user_profile_partial
from app.schemas.profile import ProfileUpdateResult

logger = logging.getLogger(__name__)


# ============================================================================
# System Prompts
# ============================================================================

PROFILE_EXTRACTION_PROMPT = """你是一个专业的购车顾问助手，专注于从对话中提取用户的购车偏好。

## 任务
分析用户的最新消息，判断用户是否表达了**修改**购车偏好（品牌、预算、标签）的意图。

## 提取规则
1. **只提取变更**: 仅当用户明确表达了新的偏好或修改原有偏好时，才设置对应字段。
2. **Has Changed**: 如果提取到任何变更，必须将 `has_changed` 设为 true。如果只是闲聊或询问车辆信息但未表达偏好变更，设为 false。
3. **Tags**:
    - `tags_to_add`: 用户新提到的需求标签（如“想要省油的”，“要有推背感”）。
    - `tags_to_remove`: 用户明确表示不想要的标签（如“不要电车” -> 可能隐含移除“纯电”标签，或需负面标签处理。此处简化为移除旧偏好）。
4. **Brand/Budget**: 仅在用户明确指定时提取。

## 示例
- 用户: "有没有宝马3系？" -> has_changed=True, new_brand="宝马"
- 用户: "预算大概30万左右" -> has_changed=True, new_budget_min=25, new_budget_max=35 (估算)
- 用户: "这就太贵了" -> has_changed=False (模糊，不提取)
- 用户: "我不喜欢奥迪，看看奔驰" -> has_changed=True, new_brand="奔驰"
- 用户: "你好" -> has_changed=False

## 输出格式
{format_instructions}
"""

INTENT_SYSTEM_PROMPT = """你是一个汽车销售助手的意图分析器。

## 任务
分析用户的最新消息，判断其意图并提取相关参数。

## 意图分类
1. **search** - 用户想查找、比较或获取车辆推荐
   - 关键词: 找车、有没有、推荐、比价、想买、预算、什么车
2. **chat** - 普通闲聊或与车辆无关的问题
   - 关键词: 你好、谢谢、帮助、其他话题
3. **calculate** - 用户想计算费用（分期、保险、税费等）
   - 关键词: 分期、月供、首付、保险、落地价

## 搜索参数提取 (仅当 intent 为 "search" 时)
从用户消息中提取以下参数（未提及则为 null）：
- query: 用户描述的车辆特征或需求（字符串）
- min_price: 最低预算，单位万元（整数）
- max_price: 最高预算，单位万元（整数）
- brand: 品牌名称（字符串，如 "宝马", "奔驰"）
- tags: 车辆标签列表（如 ["SUV", "省油", "家用"]）

## 输出格式
你必须且只能输出一个 JSON 对象，不要有其他文字：
```json
{
  "intent": "search" | "chat" | "calculate",
  "search_params": {
    "query": "...",
    "min_price": ...,
    "max_price": ...,
    "brand": "...",
    "tags": [...]
  }
}
```

如果用户没有明确指定某些参数，可以参考用户画像中的偏好作为默认值。
如果 intent 不是 "search"，search_params 可以为 null 或空对象 {}。
"""


# ============================================================================
# Helper Functions
# ============================================================================

def extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from LLM response text.
    
    Handles cases where LLM might wrap JSON in markdown code blocks
    or include extra text before/after the JSON.
    
    Args:
        text: Raw LLM response text.
        
    Returns:
        Parsed JSON dict, or None if parsing fails.
    """
    # Try direct parsing first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code blocks
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    matches = re.findall(code_block_pattern, text)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # Try finding JSON object pattern
    json_pattern = r'\{[\s\S]*\}'
    matches = re.findall(json_pattern, text)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None


# ============================================================================
# Node Functions
# ============================================================================

async def extract_profile(state: AgentState) -> Dict[str, Any]:
    """
    Profile Extraction Node: Extract and update user preferences.
    """
    logger.info("[Node: extract_profile] Checking for profile updates...")
    
    user_id = state.get("user_id")
    if not user_id:
        return {}
        
    # 只分析最后一条用户消息
    messages = state.get("messages", [])
    if not messages:
        return {}
        
    last_message = messages[-1]
    # 确保是 HumanMessage
    if not isinstance(last_message, HumanMessage):
        return {}
        
    try:
        # 使用 PydanticOutputParser 降级方案
        llm = LLMFactory.get_llm(temperature=0.0)
        
        parser = PydanticOutputParser(pydantic_object=ProfileUpdateResult)
        
        prompt = PromptTemplate(
            template=PROFILE_EXTRACTION_PROMPT + "\n用户最新消息: {message}",
            input_variables=["message"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt | llm | parser
        
        # Invoke
        result = await chain.ainvoke({"message": last_message.content})
        
        if result.has_changed:
            logger.info(f"[Node: extract_profile] Extracted changes: {result}")
            await update_user_profile_partial(str(user_id), result)
            
            # 这里不直接更新 state，因为 identify_intent 节点会重新读取最新的 profile summary
            
    except Exception as e:
        logger.error(f"[Node: extract_profile] Error: {e}")
        
    return {}


async def identify_intent(state: AgentState) -> Dict[str, Any]:
    """
    Intent Router Node: Analyze user message and classify intent.
    
    This node uses LLM to:
    1. Classify user intent (search/chat/calculate)
    2. Extract search parameters if intent is "search"
    
    Args:
        state: Current agent state containing messages.
        
    Returns:
        Dict with 'intent' and 'search_params' to update state.
    """
    logger.info("[Node: identify_intent] Starting intent classification...")
    
    # Default fallback values
    default_result = {
        "intent": "chat",
        "search_params": None,
        "step_count": 1  # Increment step counter
    }
    
    try:
        # Get LLM instance (low temperature for consistent classification)
        llm = LLMFactory.get_llm(temperature=0.1, streaming=False)
        
        # Build messages for LLM
        messages = state.get("messages", [])
        if not messages:
            logger.warning("[Node: identify_intent] No messages in state, returning default")
            return default_result
        
        # Fetch user profile for personalization (graceful degradation)
        user_id = state.get("user_id")
        user_profile_section = ""
        
        if user_id:
            try:
                profile_summary = await get_user_profile_summary(user_id)
                if profile_summary and profile_summary != "暂无用户偏好记录":
                    user_profile_section = f"""## 用户画像
该用户的历史偏好记录如下，仅供参考（如用户本次明确指定则以用户为准）：
{profile_summary}
"""
                    logger.debug(f"[Node: identify_intent] Injected user profile for user={user_id}")
            except Exception as e:
                logger.warning(f"[Node: identify_intent] Failed to get user profile: {e}")
                # Continue without profile - graceful degradation
        
        # Build system prompt with optional user profile
        system_prompt = INTENT_SYSTEM_PROMPT + "\n" + user_profile_section if user_profile_section else INTENT_SYSTEM_PROMPT
        
        # Construct prompt with system instruction and conversation history
        llm_messages = [
            SystemMessage(content=system_prompt),
        ]
        
        # Add recent conversation history (last 5 messages for context)
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        for msg in recent_messages:
            llm_messages.append(msg)
        
        # Invoke LLM
        logger.debug(f"[Node: identify_intent] Invoking LLM with {len(llm_messages)} messages")
        response = await llm.ainvoke(llm_messages)
        response_text = response.content
        
        logger.debug(f"[Node: identify_intent] LLM response: {response_text[:200]}...")
        
        # Parse JSON from response
        parsed = extract_json_from_response(response_text)
        
        if parsed is None:
            logger.warning("[Node: identify_intent] Failed to parse JSON, falling back to 'chat'")
            return default_result
        
        # Extract intent and search_params
        intent = parsed.get("intent", "chat")
        search_params = parsed.get("search_params")
        
        # Validate intent value
        if intent not in ("search", "chat", "calculate"):
            logger.warning(f"[Node: identify_intent] Invalid intent '{intent}', falling back to 'chat'")
            intent = "chat"
        
        # Clean up search_params if intent is not search
        if intent != "search":
            search_params = None
        
        logger.info(f"[Node: identify_intent] Classified intent: {intent}")
        
        return {
            "intent": intent,
            "search_params": search_params,
            "step_count": 1  # Increment step counter
        }
        
    except Exception as e:
        logger.error(f"[Node: identify_intent] Error: {e}", exc_info=True)
        return default_result


async def execute_search(state: AgentState) -> Dict[str, Any]:
    """
    Tool Execution Node: Execute vehicle search using VehicleSearchTool.
    
    This node:
    1. Extracts search parameters from state
    2. Invokes VehicleSearchTool._arun() with those parameters
    3. Returns the tool output as a string
    
    Args:
        state: Current agent state containing search_params.
        
    Returns:
        Dict with 'tool_output' to update state.
    """
    logger.info("[Node: execute_search] Starting vehicle search...")
    
    try:
        # Get search parameters from state
        search_params = state.get("search_params") or {}
        
        logger.debug(f"[Node: execute_search] Search params: {search_params}")
        
        # Instantiate the search tool
        tool = VehicleSearchTool()
        
        # Extract individual parameters with defaults
        query = search_params.get("query")
        min_price = search_params.get("min_price")
        max_price = search_params.get("max_price")
        brand = search_params.get("brand")
        tags = search_params.get("tags")
        sort_strategy = search_params.get("sort_strategy", "default")
        
        # Execute async search
        result = await tool._arun(
            query=query,
            min_price=min_price,
            max_price=max_price,
            brand=brand,
            tags=tags,
            sort_strategy=sort_strategy
        )
        
        logger.info(f"[Node: execute_search] Search completed, result length: {len(result)} chars")
        
        return {
            "tool_output": result,
            "step_count": 1  # Increment step counter
        }
        
    except Exception as e:
        error_msg = f"[搜索执行失败] {str(e)}"
        logger.error(f"[Node: execute_search] Error: {e}", exc_info=True)
        
        return {
            "tool_output": error_msg,
            "step_count": 1
        }
