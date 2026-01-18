# app/utils/json_extractor.py
"""
JSON 提取工具：从 LLM 返回的文本中提取 JSON（处理 Markdown 代码块）
"""
import json
import re
from typing import Any, Dict, Optional


def extract_json_from_text(text: str) -> str:
    """
    从文本中提取 JSON，支持以下格式：
    1. Markdown 代码块：```json {...} ```
    2. 纯 JSON：{...}
    3. 带说明的 JSON：... 以下是JSON: {...} ...
    
    Args:
        text: LLM 返回的文本
    
    Returns:
        提取的 JSON 字符串
    
    Raises:
        ValueError: 如果无法提取有效的 JSON
    """
    if not text or not text.strip():
        raise ValueError("输入文本为空")
    
    text = text.strip()
    
    # 1. 尝试匹配 Markdown 代码块 ```json ... ```
    json_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    match = re.search(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        json_str = match.group(1).strip()
        # 验证是否是有效的 JSON
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass
    
    # 2. 尝试匹配纯 JSON 对象 {...}
    json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_obj_pattern, text, re.DOTALL)
    for match in matches:
        try:
            json.loads(match)
            return match
        except json.JSONDecodeError:
            continue
    
    # 3. 如果都不行，尝试直接解析整个文本
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    
    # 4. 如果还是不行，抛出异常
    raise ValueError(f"无法从文本中提取有效的 JSON:\n{text[:200]}")


def safe_json_loads(text: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    安全地解析 JSON，自动处理 Markdown 代码块
    
    Args:
        text: LLM 返回的文本
        default: 解析失败时的默认值
    
    Returns:
        解析后的 JSON 字典
    """
    try:
        json_str = extract_json_from_text(text)
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as e:
        if default is not None:
            return default
        raise ValueError(f"JSON 解析失败: {e}\n原始文本: {text[:200]}")
