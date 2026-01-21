from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class CarDetailResponse(BaseModel):
    id: int
    name: str
    year: str
    price: float = Field(..., description="指导价(万)")
    status: int

    # 关联信息
    brand_name: str
    brand_logo: Optional[str]
    series_name: str
    series_level: str
    energy_type: str

    # 扩展信息
    extra_tags: Optional[Dict[str, Any]] = None

    # 为了前端展示方便，我们在这里模拟一些图片字段 (实际项目中可能存在 MongoDB 或 OSS)
    images: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True