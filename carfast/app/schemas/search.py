from typing import Optional, List
from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    q: Optional[str] = Field(None, description="搜索关键词")

    # --- 筛选条件 ---
    brand: Optional[str] = Field(None, description="品牌名称筛选 (精确匹配)")
    series_level: Optional[str] = Field(None, description="级别筛选 (如: SUV, 紧凑型车)")
    energy_type: Optional[str] = Field(None, description="能源类型 (如: 纯电, 插混)")

    min_price: Optional[float] = Field(None, description="最低价格 (万)")
    max_price: Optional[float] = Field(None, description="最高价格 (万)")

    # --- 排序与分页 ---
    sort_by: str = Field("default", description="排序字段: default(综合), price_asc, price_desc, new")
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)