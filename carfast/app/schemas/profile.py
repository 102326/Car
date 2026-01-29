from pydantic import BaseModel, Field
from typing import Optional, List

class ProfileUpdateResult(BaseModel):
    """LLM 提取的用户画像变更意图"""
    has_changed: bool = Field(description="用户是否表达了修改购车偏好(品牌/预算/标签)的意图")
    new_brand: Optional[str] = Field(None, description="新的偏好品牌(如'宝马')，如果用户明确切换品牌则填入")
    new_budget_min: Optional[int] = Field(None, description="新的预算下限(万)")
    new_budget_max: Optional[int] = Field(None, description="新的预算上限(万)")
    tags_to_add: List[str] = Field(default_factory=list, description="需要新增的偏好标签(如'省油')")
    tags_to_remove: List[str] = Field(default_factory=list, description="需要移除的标签")
