from typing import Optional, List, Any
from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    """
    统一搜索参数模型
    """
    q: Optional[str] = Field(None, description="搜索关键词")

    # 筛选
    min_price: Optional[float] = Field(None, description="最低价(万)")
    max_price: Optional[float] = Field(None, description="最高价(万)")
    brand: Optional[str] = Field(None, description="品牌")
    series: Optional[str] = Field(None, description="车系")
    tags: Optional[List[str]] = Field(None, description="标签")

    # 分页
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=50)

    # 排序: default, price_asc, price_desc, new
    sort_by: str = Field("default")


class CarDoc(BaseModel):
    id: int
    name: str
    price: float
    brand: str
    image: Optional[str] = None
    description: Optional[str] = None
    status: int
    name_highlight: Optional[str] = None  # 高亮
    desc_highlight: Optional[str] = None


class SearchResponse(BaseModel):
    total: int
    list: List[CarDoc]
    page: int
    size: int