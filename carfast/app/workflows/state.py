"""
Agent State Schema for CarFast LangGraph Agent.
(真·封神版) 包含读时衰减 (Read-time Decay)、多维度半衰期、EMA 平滑与 GC 回收。
"""

import copy
import time
import math
from typing import Annotated, Any, Dict, List, Optional, TypedDict
import operator
from langchain_core.messages import BaseMessage

# ============================================================================
# 🌟 企业级多维度半衰期配置 (按秒计算)
# ============================================================================
HALF_LIFE_MAP = {
    "preference_tags": 86400 * 3,   # 兴趣标签：半衰期 3 天 (变得快)
    "preference_brand": 86400 * 7,  # 品牌偏好：半衰期 7 天 (相对稳定)
    "budget_min": float('inf'),     # 预算：无穷大 (除非用户明确改口，否则绝不衰减)
    "budget_max": float('inf'),
    "default": 86400                # 默认：1 天
}

def get_decay_rate(key: str) -> float:
    """计算特定字段的指数衰减率 λ"""
    hl = HALF_LIFE_MAP.get(key, HALF_LIFE_MAP["default"])
    if hl == float('inf'):
        return 0.0
    return math.log(2) / hl

# ============================================================================
# 🌟 核心补丁：读时衰减 (Read-time Decay)
# ============================================================================
def apply_read_time_decay(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    【推荐系统标准做法】：在提取画像给大模型使用前，主动执行一次基于真实时间差的衰减。
    解决“用户不说话就不触发遗忘”的懒执行 (Lazy Evaluation) 漏洞。
    """
    if not profile or "_meta" not in profile:
        return profile

    current_time = time.time()
    meta = profile["_meta"]

    # 需要被 GC 清理的废弃 key
    keys_to_remove = []

    for weight_key, old_weight in meta.get("weights", {}).items():
        # weight_key 格式通常是 "preference_tags_纯电"
        field_name = weight_key.split("_")[0] + "_" + weight_key.split("_")[1] if "_" in weight_key else weight_key

        last_time = meta["timestamps"].get(weight_key, current_time)
        delta_t = max(0, current_time - last_time)

        # 应用指数衰减
        decay_rate = get_decay_rate(field_name)
        new_weight = old_weight * math.exp(-decay_rate * delta_t)

        if new_weight > 0.3:
            meta["weights"][weight_key] = new_weight
            # 注意：读时衰减【不更新】时间戳，因为用户并没有真实提及
        else:
            keys_to_remove.append(weight_key)

    # 垃圾回收 (GC) & 剔除过期标签
    for k in keys_to_remove:
        meta["weights"].pop(k, None)
        meta["timestamps"].pop(k, None)

        # 同步从真实 profile 列表中删除
        field = k.split("_")[0] + "_" + k.split("_")[1] if k.count("_") >= 2 else k.split("_")[0]
        tag_value = k.split("_")[-1]

        if field in profile and isinstance(profile[field], list):
            profile[field] = [t for t in profile[field] if t != tag_value]

    return profile

# ============================================================================
# 工业级合并 Reducers
# ============================================================================
def merge_dicts_with_decay(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """写时更新 (Write-time Update) 结合 EMA 平滑"""
    if not left: return copy.deepcopy(right) if right else {}
    if not right: return copy.deepcopy(left)

    merged = copy.deepcopy(left)
    current_time = time.time()

    if "_meta" not in merged:
        merged["_meta"] = {"timestamps": {}, "weights": {}}

    for k, v in right.items():
        if k == "_meta": continue

        decay_rate = get_decay_rate(k)

        # 处理带显式增加/减少的标签集合
        if isinstance(v, dict) and ("_add" in v or "_remove" in v):
            if k not in merged: merged[k] = []

            adds = set(v.get("_add", []))
            removes = set(v.get("_remove", []))
            old_items = set(merged[k])
            final_items = []

            for item in old_items | adds | removes:
                weight_key = f"{k}_{item}"
                old_weight = merged["_meta"]["weights"].get(weight_key, 0.5)
                last_time = merged["_meta"]["timestamps"].get(weight_key, current_time)

                delta_t = max(0, current_time - last_time)
                decayed_weight = old_weight * math.exp(-decay_rate * delta_t)

                if item in removes:
                    new_weight = 0.0 # 显式否定
                elif item in adds:
                    new_weight = decayed_weight + 0.4 * (1.0 - decayed_weight) # EMA 平滑
                else:
                    new_weight = decayed_weight

                if new_weight > 0.3:
                    final_items.append(item)
                    merged["_meta"]["weights"][weight_key] = new_weight
                    # 只有发生真实更新(add)，才刷新时间戳
                    if item in adds:
                        merged["_meta"]["timestamps"][weight_key] = current_time
                else:
                    merged["_meta"]["weights"].pop(weight_key, None)
                    merged["_meta"]["timestamps"].pop(weight_key, None)

            merged[k] = final_items
            continue

        # 字典深合并
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = merge_dicts_with_decay(merged[k], v)
        else:
            # 普通字段直接覆盖
            if v is not None:
                merged[k] = v
                merged["_meta"]["timestamps"][k] = current_time

    return merged

def increment_count(left: int, right: int) -> int:
    return (left or 0) + (right or 0)

class AgentState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: Optional[str]
    user_profile: Annotated[Dict[str, Any], merge_dicts_with_decay]
    intent: Optional[str]
    search_params: Optional[Dict[str, Any]]
    calculate_params: Optional[Dict[str, Any]]
    tool_output: Optional[str]
    critic_decision: Optional[str]
    critic_reason: Optional[str]
    observation: Optional[str]
    evaluation_result: Optional[str]
    step_count: Annotated[int, increment_count]