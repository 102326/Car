from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    q: Optional[str] = Field(None, description="搜索关键词")

    # --- 筛选条件 ---
    brand: Optional[str] = Field(None, description="品牌名称筛选 (精确匹配)")
    series_level: Optional[str] = Field(None, description="级别筛选 (如: SUV, 紧凑型车)")
    energy_type: Optional[str] = Field(None, description="能源类型 (如: 纯电, 插混)")
    #11
    min_price: Optional[float] = Field(None, description="最低价格 (万)")
    max_price: Optional[float] = Field(None, description="最高价格 (万)")

    # --- 排序与分页 ---
    sort_by: str = Field("default", description="排序字段: default(综合), price_asc, price_desc, new")
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

class VehicleSearchInput(BaseModel):
    """
    车辆库存搜索工具的输入参数。
    Agent 应根据用户意图提取关键词、预算范围和品牌偏好。
    """
    query: Optional[str] = Field(
        default=None,
        description="模糊搜索词，用于匹配车型名称或描述。例如：'宝马X5'、'黑色轿车'。如果用户只提供了预算或品牌，此项可为空。"
    )
    min_price: Optional[int] = Field(
        default=None,
        description="最低预算（万元）。例如用户说'30万以上'，则此值为30。"
    )
    max_price: Optional[int] = Field(
        default=None,
        description="最高预算（万元）。例如用户说'20万左右'，可推断为15-25，此处填25。"
    )
    brand: Optional[str] = Field(
        default=None,
        description="明确的品牌名称。例如：'奥迪'、'特斯拉'。"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="车辆特征标签。常见标签：['准新车', '家用', '省油', '急售', '练手车']。"
    )
    sort_strategy: Literal["default", "price_lowest", "price_highest", "newest"] = Field(
        default="default",
        description="排序策略。'default'=综合排序, 'price_lowest'=价格从低到高, 'price_highest'=价格从高到低, 'newest'=最新上架。"
    )