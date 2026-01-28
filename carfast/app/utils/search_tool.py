from typing import Type, List, Optional, Literal, ClassVar, Dict
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# 1. 引入项目现有核心逻辑
from app.services.es_service import CarESService  # ✅ 修正为 CarESService
from app.schemas.search import SearchParams, VehicleSearchInput  # ✅ 复用已定义的 Input Schema


class VehicleSearchTool(BaseTool):
    name: str = "vehicle_inventory_search"
    description: str = (
        "用于查询车辆实时库存信息。"
        "当你需要回答关于'有没有车'、'找车'、'比价'或'推荐车辆'的问题时，必须使用此工具。"
        "它会返回符合条件的车辆列表概要和统计建议。"
    )
    args_schema: Type[BaseModel] = VehicleSearchInput

    # 排序策略映射表：Agent 语言 -> 系统字段 (SearchParams.sort_by)
    SORT_MAPPING: ClassVar[Dict[str, str]] = {
        "default": "default",
        "price_lowest": "price_asc",
        "price_highest": "price_desc",
        "newest": "new"  # ✅ 对应 es_service.py 中的 "new"
    }

    def _run(self, *args, **kwargs):
        """同步调用入口（FastAPI 环境下通常不被直接调用，但必须实现）"""
        raise NotImplementedError("VehicleSearchTool only supports async execution via _arun")

    async def _arun(
            self,
            query: Optional[str] = None,
            min_price: Optional[int] = None,
            max_price: Optional[int] = None,
            brand: Optional[str] = None,
            tags: Optional[List[str]] = None,
            sort_strategy: str = "default"
    ) -> str:
        """
        异步执行车辆搜索，并返回元认知报告。
        """
        # 1. 构造系统底层 SearchParams
        # 注意: es_service.py 中 tags 目前主要通过 tags_text 的全文检索匹配，
        # 或者后续扩展 filter。这里暂时将 tags合并入 query 或忽略，
        # 既然 search_cars_pro 还没显式处理 tags 列表过滤，我们先把 tags 加到 query 里增强匹配

        final_query = query or ""
        if tags:
            tag_str = " ".join(tags)
            final_query = f"{final_query} {tag_str}".strip()

        # 强制锁定分页为 Top 5，避免 Agent 阅读大量数据
        search_params = SearchParams(
            q=final_query if final_query else None,
            min_price=float(min_price) if min_price is not None else None,  # ✅ 转 float
            max_price=float(max_price) if max_price is not None else None,  # ✅ 转 float
            brand=brand,
            # series_level 可以留空，暂不开放给 Agent
            page=1,
            size=5,
            sort_by=self.SORT_MAPPING.get(sort_strategy, "default")
        )

        # 2. 调用 ES 服务 (核心能力)
        # ✅ 使用 CarESService.search_cars_pro
        result = await CarESService.search_cars_pro(search_params)

        # 3. 生成元认知报告 (Summary + Data + Suggestion)
        return self._format_meta_response(result)

    def _format_meta_response(self, result: dict) -> str:
        """
        将 ES 返回的 JSON 转换为 Agent 易读的自然语言报告。
        """
        total = result.get("total", 0)
        items = result.get("list", [])  # ✅ 对应 search_cars_pro 返回的 key 是 "list"
        facets = result.get("facets", {})  # ✅ 对应 search_cars_pro 返回的 key 是 "facets"

        # Part 1: 摘要 (Summary)
        summary = f"[库存摘要]\n共找到 {total} 辆符合条件的车辆。"
        if total > 5:
            summary += " (仅展示相关性最高的 Top 5)"
        elif total == 0:
            return f"[库存摘要]\n未找到符合条件的车辆。\n\n[建议]\n库存中没有匹配项。建议尝试放宽价格范围或减少标签限制。"

        # Part 2: 数据快照 (Data Snapshot)
        # 格式: ID | 标题 | 价格 | 关键标签
        data_lines = ["[精选车源]"]
        for car in items:
            c_id = car.get("id")
            c_name = car.get("name_highlight", car.get("name"))  # ✅ 优先展示高亮名
            c_price = car.get("price")
            # 简单展示关键属性
            c_info = f"{car.get('year', '')}款 {car.get('series_level', '')}"

            data_lines.append(f"- ID:{c_id} | {c_name} | {c_price}万 | {c_info}")

        data_section = "\n".join(data_lines)

        # Part 3: 决策建议 (Suggestion from Facets)
        suggestions = ["[交互建议]"]

        # 分析品牌分布
        brands = facets.get("brands", [])
        if brands and len(brands) > 1:
            top_brands = ", ".join(brands[:3])
            suggestions.append(f"当前结果包含多个品牌: {top_brands}。如果用户未指定品牌，可询问其品牌偏好。")

        # 分析级别分布
        levels = facets.get("levels", [])
        if levels and len(levels) > 1:
            suggestions.append(f"车型级别分布: {', '.join(levels[:3])}。")

        if len(suggestions) == 1:
            suggestions.append("结果精准，可直接根据上述车源回答用户。")   

        suggestion_section = "\n".join(suggestions)

        # 最终组合
        return f"{summary}\n\n{data_section}\n\n{suggestion_section}"