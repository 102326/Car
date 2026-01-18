# app/agents/enrichment_graph.py
"""
数据补充 Agent 的 LangGraph 工作流
"""
from typing import TypedDict, Dict, Any, Optional, Literal
from datetime import datetime
from sqlalchemy import select
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from app.core.database import AsyncSessionLocal
from app.models.car import CarBrand, CarSeries, CarModel
from app.agents.tools.web_scraper import fetch_autohome_data, search_car_info
from app.utils.model_factory import ModelFactory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# ==========================================
# Pydantic Schemas
# ==========================================
class EnrichmentInput(BaseModel):
    """数据补充输入"""
    car_series_name: str = Field(..., description="车系名称", min_length=1, max_length=100)
    force_refresh: bool = Field(False, description="是否强制刷新（即使数据库有数据）")
    user_city: Optional[str] = Field(None, description="用户城市（用于本地化数据）")


class EnrichmentOutput(BaseModel):
    """数据补充输出"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="执行消息")
    data: Optional[Dict[str, Any]] = Field(None, description="补充的数据")
    source: str = Field(..., description="数据来源（db/web/api）")
    update_time: str = Field(..., description="更新时间")


# ==========================================
# Graph State
# ==========================================
class EnrichmentState(TypedDict):
    """数据补充工作流状态"""
    # 输入
    car_series_name: str
    force_refresh: bool
    user_city: Optional[str]
    
    # 中间状态
    db_exists: bool  # 数据库是否已有数据
    db_data: Optional[Dict[str, Any]]  # 数据库查询结果
    selected_tool: Optional[str]  # 选择的抓取工具（"autohome" / "tavily"）
    raw_data: Optional[Dict[str, Any]]  # 原始抓取数据
    parsed_data: Optional[Dict[str, Any]]  # 解析后的标准数据
    
    # 输出
    success: bool
    message: str
    final_data: Optional[Dict[str, Any]]
    source: str
    
    # 元数据
    metadata: Optional[Dict[str, Any]]


# ==========================================
# System Prompt for LLM
# ==========================================
DATA_EXTRACTION_PROMPT = """
你是一个数据提取专家，负责从混乱的网页文本中提取标准的车型参数。

## 输入数据
{raw_content}

## 提取目标
从上述文本中提取以下字段（JSON格式）：

```json
{{
    "brand": {{
        "name": "品牌中文名（如：比亚迪）",
        "name_en": "品牌英文名（如：BYD）",
        "country": "所属国家（中国/美国/德国/日本等）"
    }},
    "series": {{
        "name": "车系名称（如：秦PLUS DM-i）",
        "level": "车身级别（紧凑型车/中型车/SUV/MPV）",
        "energy_type": "能源类型（纯电动/插电式混合动力/燃油/油电混合）",
        "min_price_guidance": 最低指导价（单位：万元，如：11.98）,
        "max_price_guidance": 最高指导价（单位：万元，如：15.98）
    }},
    "models": [
        {{
            "name": "具体款型名称（如：2026款 DM-i 120km 冠军版）",
            "year": "年款（如：2026）",
            "price_guidance": 指导价（单位：万元，如：11.98）,
            "status": 1,  // 1=在售, 0=停售, 2=未上市
            "extra_tags": {{
                "subsidy": 补贴金额（万元），
                "tags": ["免购置税", "包含充电桩"]  // 营销标签
            }}
        }}
    ]
}}
```

## 提取规则
1. **品牌识别**：根据车系名称推断品牌（如"秦PLUS"->比亚迪，"Model 3"->特斯拉）
2. **价格单位**：统一转换为"万元"（如：119800元 -> 11.98万）
3. **级别判断**：根据车型尺寸/定位判断（轴距>2700mm通常是中型车）
4. **能源类型**：
   - DM-i/PHEV -> 插电式混合动力
   - EV/纯电 -> 纯电动
   - HEV/混动 -> 油电混合
   - 汽油/柴油 -> 燃油
5. **状态判断**：
   - 文本包含"在售"/"现售" -> status=1
   - 文本包含"停售"/"已停产" -> status=0
   - 文本包含"未上市"/"即将上市" -> status=2

## 缺失数据处理
- 如果某个字段无法提取，填写 `null` 或 `"未知"`
- 如果价格范围无法确定，min_price 和 max_price 可以相同
- models 数组至少包含1个元素

## 输出格式
严格按照上述 JSON 格式输出，不要添加任何额外的文字说明。
如果提取失败，返回：
```json
{{"error": "提取失败的原因"}}
```

现在，请提取数据：
"""


# ==========================================
# Graph Nodes
# ==========================================

async def check_db_node(state: EnrichmentState) -> Dict[str, Any]:
    """
    节点1: 检查数据库是否已有数据
    """
    from app.core.logging_config import StructuredLogger
    import time
    
    start_time = time.time()
    logger_struct = StructuredLogger("agent.enrichment.check_db")
    
    car_series_name = state["car_series_name"]
    force_refresh = state.get("force_refresh", False)
    
    logger_struct.log_event("check_db_start", {
        "car_series_name": car_series_name,
        "force_refresh": force_refresh
    })
    
    print(f"\n[CheckDB] 检查数据库: {car_series_name}")
    
    # 如果强制刷新，跳过数据库检查
    if force_refresh:
        print(f"[CheckDB] 强制刷新模式，跳过数据库检查")
        return {
            "db_exists": False,
            "db_data": None,
            "metadata": {"check_time": datetime.now().isoformat()}
        }
    
    try:
        # 查询数据库（正确用法：直接创建会话）
        async with AsyncSessionLocal() as session:
            stmt = select(CarSeries).where(CarSeries.name.like(f"%{car_series_name}%"))
            result = await session.execute(stmt)
            car_series = result.scalar_one_or_none()
            
            if car_series:
                # 查询该车系下的车型
                stmt_models = select(CarModel).where(
                    CarModel.series_id == car_series.id,
                    CarModel.status == 1
                )
                result_models = await session.execute(stmt_models)
                models = result_models.scalars().all()
                
                db_data = {
                    "brand": {
                        "id": car_series.brand.id if car_series.brand else None,
                        "name": car_series.brand.name if car_series.brand else "未知"
                    },
                    "series": {
                        "id": car_series.id,
                        "name": car_series.name,
                        "level": car_series.level,
                        "energy_type": car_series.energy_type,
                        "price_range": f"{car_series.min_price_guidance}-{car_series.max_price_guidance}万"
                    },
                    "models": [
                        {
                            "id": model.id,
                            "name": model.name,
                            "year": model.year,
                            "price_guidance": float(model.price_guidance),
                            "status": model.status
                        }
                        for model in models
                    ]
                }
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                print(f"[CheckDB] ✅ 数据库已有数据，找到 {len(models)} 个车型")
                
                logger_struct.log_event("check_db_found", {
                    "models_count": len(models),
                    "elapsed_ms": elapsed_ms
                })
                
                return {
                    "db_exists": True,
                    "db_data": db_data,
                    "source": "db",
                    "metadata": {"db_check": "found", "models_count": len(models), "elapsed_ms": elapsed_ms}
                }
            else:
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                print(f"[CheckDB] ❌ 数据库无数据")
                
                logger_struct.log_event("check_db_not_found", {
                    "elapsed_ms": elapsed_ms
                })
                
                return {
                    "db_exists": False,
                    "db_data": None,
                    "metadata": {"db_check": "not_found", "elapsed_ms": elapsed_ms}
                }
            
    except Exception as e:
        print(f"[CheckDB] 查询失败: {e}")
        return {
            "db_exists": False,
            "db_data": None,
            "metadata": {"db_check": "error", "error": str(e)}
        }


async def decide_tool_node(state: EnrichmentState) -> Dict[str, Any]:
    """
    节点2: 决定使用哪个抓取工具
    """
    car_series_name = state["car_series_name"]
    
    print(f"\n[DecideTool] 选择抓取工具")
    
    # 简单的决策逻辑（可以扩展为更复杂的规则）
    # 优先级: autohome > tavily
    selected_tool = "autohome"
    
    # 也可以根据车系名称选择不同工具
    # if "进口" in car_series_name or "海外" in car_series_name:
    #     selected_tool = "tavily"
    
    print(f"[DecideTool] 选择工具: {selected_tool}")
    
    return {
        "selected_tool": selected_tool,
        "metadata": {"tool_selection": selected_tool}
    }


async def fetch_data_node(state: EnrichmentState) -> Dict[str, Any]:
    """
    节点3: 执行数据抓取
    """
    car_series_name = state["car_series_name"]
    selected_tool = state["selected_tool"]
    
    print(f"\n[FetchData] 使用 {selected_tool} 抓取数据")
    
    try:
        if selected_tool == "autohome":
            result = await fetch_autohome_data(car_series_name, retry=3)
        elif selected_tool == "tavily":
            result = await search_car_info(car_series_name, search_engine="tavily")
        else:
            result = {"success": False, "message": f"未知工具: {selected_tool}"}
        
        if result["success"]:
            print(f"[FetchData] ✅ 抓取成功")
            return {
                "raw_data": result.get("data", {}),
                "metadata": {
                    "fetch_status": "success",
                    "fetch_message": result.get("message", "")
                }
            }
        else:
            print(f"[FetchData] ❌ 抓取失败: {result.get('message')}")
            return {
                "raw_data": None,
                "success": False,
                "message": f"抓取失败: {result.get('message')}",
                "metadata": {"fetch_status": "failed"}
            }
            
    except Exception as e:
        print(f"[FetchData] 异常: {e}")
        return {
            "raw_data": None,
            "success": False,
            "message": f"抓取异常: {str(e)}",
            "metadata": {"fetch_status": "error", "error": str(e)}
        }


async def parse_data_node(state: EnrichmentState) -> Dict[str, Any]:
    """
    节点3.5: 使用 LLM 解析抓取的数据（可选）
    
    如果 raw_data 已经是结构化数据，可以跳过此节点
    """
    raw_data = state.get("raw_data")
    
    if not raw_data:
        return {"parsed_data": None}
    
    # 如果 raw_data 已经是结构化的（如 autohome 工具返回的），直接使用
    if "brand" in raw_data and "series" in raw_data:
        print(f"[ParseData] 数据已结构化，跳过解析")
        return {"parsed_data": raw_data}
    
    # 否则，使用 LLM 解析混乱的文本
    print(f"\n[ParseData] 使用 LLM 解析原始数据")
    
    try:
        # 使用"大脑"模型进行数据提取（复杂任务）
        llm = ModelFactory.get_brain_model(temperature=0.1)
        prompt = ChatPromptTemplate.from_template(DATA_EXTRACTION_PROMPT)
        chain = prompt | llm | StrOutputParser()
        
        result = await chain.ainvoke({
            "raw_content": str(raw_data.get("raw_content", raw_data))
        })
        
        # 解析 JSON
        import json
        parsed_data = json.loads(result)
        
        if "error" in parsed_data:
            print(f"[ParseData] LLM 提取失败: {parsed_data['error']}")
            return {"parsed_data": None, "message": f"数据解析失败: {parsed_data['error']}"}
        
        print(f"[ParseData] ✅ LLM 解析成功")
        return {"parsed_data": parsed_data}
        
    except Exception as e:
        print(f"[ParseData] 解析异常: {e}")
        return {"parsed_data": None, "message": f"数据解析异常: {str(e)}"}


async def save_to_db_node(state: EnrichmentState) -> Dict[str, Any]:
    """
    节点4: 将数据保存到数据库
    """
    parsed_data = state.get("parsed_data") or state.get("raw_data")
    
    if not parsed_data:
        return {
            "success": False,
            "message": "没有可保存的数据",
            "source": "none"
        }
    
    print(f"\n[SaveToDB] 保存数据到数据库")
    
    try:
        # 保存数据到数据库（正确用法：直接创建会话）
        async with AsyncSessionLocal() as session:
            try:
                # 1. 保存品牌
            brand_data = parsed_data.get("brand", {})
            brand_name = brand_data.get("name")
            
            if not brand_name or brand_name == "未知品牌":
                print(f"[SaveToDB] ⚠️ 品牌信息缺失，跳过保存")
                return {
                    "success": False,
                    "message": "品牌信息缺失，无法保存",
                    "source": "none"
                }
            
            # 查询或创建品牌
            stmt = select(CarBrand).where(CarBrand.name == brand_name)
            result = await session.execute(stmt)
            brand = result.scalar_one_or_none()
            
            if not brand:
                brand = CarBrand(
                    name=brand_name,
                    name_en=brand_data.get("name_en", brand_name),
                    logo_url=brand_data.get("logo_url", ""),
                    first_letter=brand_name[0].upper(),
                    country=brand_data.get("country", "未知"),
                    hot_rank=0
                )
                session.add(brand)
                await session.flush()  # 获取 brand.id
                print(f"[SaveToDB] ✅ 创建品牌: {brand_name} (ID: {brand.id})")
            else:
                print(f"[SaveToDB] 品牌已存在: {brand_name} (ID: {brand.id})")
            
            # 2. 保存车系
            series_data = parsed_data.get("series", {})
            series_name = series_data.get("name")
            
            stmt = select(CarSeries).where(
                CarSeries.brand_id == brand.id,
                CarSeries.name == series_name
            )
            result = await session.execute(stmt)
            series = result.scalar_one_or_none()
            
            if not series:
                from decimal import Decimal
                series = CarSeries(
                    brand_id=brand.id,
                    name=series_name,
                    level=series_data.get("level", "未知"),
                    energy_type=series_data.get("energy_type", "未知"),
                    min_price_guidance=Decimal(str(series_data.get("min_price_guidance", 0))),
                    max_price_guidance=Decimal(str(series_data.get("max_price_guidance", 0)))
                )
                session.add(series)
                await session.flush()
                print(f"[SaveToDB] ✅ 创建车系: {series_name} (ID: {series.id})")
            else:
                print(f"[SaveToDB] 车系已存在: {series_name} (ID: {series.id})")
            
            # 3. 保存车型
            models_data = parsed_data.get("models", [])
            saved_models = []
            
            for model_data in models_data:
                model_name = model_data.get("name")
                
                stmt = select(CarModel).where(
                    CarModel.series_id == series.id,
                    CarModel.name == model_name
                )
                result = await session.execute(stmt)
                model = result.scalar_one_or_none()
                
                if not model:
                    from decimal import Decimal
                    model = CarModel(
                        series_id=series.id,
                        name=model_name,
                        year=model_data.get("year", "2026"),
                        price_guidance=Decimal(str(model_data.get("price_guidance", 0))),
                        status=model_data.get("status", 1),
                        extra_tags=model_data.get("extra_tags", {})
                    )
                    session.add(model)
                    saved_models.append(model_name)
                    print(f"[SaveToDB] ✅ 创建车型: {model_name}")
                else:
                    print(f"[SaveToDB] 车型已存在: {model_name}")
            
            # 提交事务
            await session.commit()
            
            print(f"\n[SaveToDB] 🎉 数据保存完成！")
            print(f"  - 品牌: {brand_name}")
            print(f"  - 车系: {series_name}")
            print(f"  - 新增车型: {len(saved_models)} 个")
            
            # 记录数据库操作日志
            from app.core.logging_config import StructuredLogger
            logger_db = StructuredLogger("agent.enrichment.save_db")
            logger_db.log_db_operation(
                operation="insert",
                table="car_series, car_model",
                success=True,
                elapsed_ms=0,
                details={
                    "brand": brand_name,
                    "series": series_name,
                    "models_count": len(saved_models)
                }
            )
            
                return {
                    "success": True,
                    "message": f"成功保存 {len(saved_models)} 个车型",
                    "source": "web",
                    "final_data": {
                        "brand": {"id": brand.id, "name": brand.name},
                        "series": {"id": series.id, "name": series.name},
                        "models_count": len(saved_models)
                    },
                    "metadata": {
                        "saved_models": saved_models,
                        "save_time": datetime.now().isoformat()
                    }
                }
            except Exception as e:
                await session.rollback()
                raise
            
    except Exception as e:
        print(f"[SaveToDB] 保存失败: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "message": f"保存失败: {str(e)}",
            "source": "none",
            "metadata": {"save_error": str(e)}
        }


async def response_node(state: EnrichmentState) -> Dict[str, Any]:
    """
    节点5: 生成最终响应
    """
    success = state.get("success", False)
    message = state.get("message", "")
    source = state.get("source", "unknown")
    
    print(f"\n[Response] 生成最终响应")
    
    if state.get("db_exists") and not state.get("force_refresh"):
        # 数据库已有数据，直接返回
        return {
            "success": True,
            "message": "数据库已有该车型数据",
            "final_data": state.get("db_data"),
            "source": "db"
        }
    elif success:
        # 成功抓取并保存
        return {
            "success": True,
            "message": f"✅ 数据补充完成！{message}",
            "final_data": state.get("final_data"),
            "source": source
        }
    else:
        # 失败
        return {
            "success": False,
            "message": f"❌ 数据补充失败: {message}",
            "final_data": None,
            "source": "none"
        }


# ==========================================
# 路由函数
# ==========================================
def route_after_check_db(state: EnrichmentState) -> Literal["decide_tool", "response"]:
    """检查数据库后的路由"""
    if state.get("db_exists") and not state.get("force_refresh"):
        # 数据库有数据且不强制刷新 -> 直接返回
        return "response"
    else:
        # 数据库无数据 -> 抓取数据
        return "decide_tool"


def route_after_fetch(state: EnrichmentState) -> Literal["parse_data", "response"]:
    """抓取数据后的路由"""
    if state.get("raw_data"):
        # 抓取成功 -> 解析数据
        return "parse_data"
    else:
        # 抓取失败 -> 直接返回错误
        return "response"


def route_after_parse(state: EnrichmentState) -> Literal["save_to_db", "response"]:
    """解析数据后的路由"""
    if state.get("parsed_data") or state.get("raw_data"):
        # 有可用数据 -> 保存到数据库
        return "save_to_db"
    else:
        # 解析失败 -> 直接返回错误
        return "response"


# ==========================================
# 构建 Graph
# ==========================================
def build_enrichment_graph() -> StateGraph:
    """
    构建数据补充 Agent 的工作流图
    """
    workflow = StateGraph(EnrichmentState)
    
    # 添加节点
    workflow.add_node("check_db", check_db_node)
    workflow.add_node("decide_tool", decide_tool_node)
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("parse_data", parse_data_node)
    workflow.add_node("save_to_db", save_to_db_node)
    workflow.add_node("response", response_node)
    
    # 设置入口点
    workflow.set_entry_point("check_db")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "check_db",
        route_after_check_db,
        {
            "decide_tool": "decide_tool",
            "response": "response"
        }
    )
    
    workflow.add_edge("decide_tool", "fetch_data")
    
    workflow.add_conditional_edges(
        "fetch_data",
        route_after_fetch,
        {
            "parse_data": "parse_data",
            "response": "response"
        }
    )
    
    workflow.add_conditional_edges(
        "parse_data",
        route_after_parse,
        {
            "save_to_db": "save_to_db",
            "response": "response"
        }
    )
    
    workflow.add_edge("save_to_db", "response")
    workflow.add_edge("response", END)
    
    return workflow.compile()


# ==========================================
# Agent 包装类
# ==========================================
class DataEnrichmentAgent:
    """
    数据补充智能体（包装类）
    """
    def __init__(self):
        self.graph = build_enrichment_graph()
    
    async def enrich(
        self,
        car_series_name: str,
        force_refresh: bool = False,
        user_city: Optional[str] = None
    ) -> EnrichmentOutput:
        """
        执行数据补充
        
        Args:
            car_series_name: 车系名称
            force_refresh: 是否强制刷新
            user_city: 用户城市
        
        Returns:
            EnrichmentOutput
        """
        # 初始化状态
        initial_state = EnrichmentState(
            car_series_name=car_series_name,
            force_refresh=force_refresh,
            user_city=user_city,
            db_exists=False,
            db_data=None,
            selected_tool=None,
            raw_data=None,
            parsed_data=None,
            success=False,
            message="",
            final_data=None,
            source="unknown",
            metadata={}
        )
        
        # 执行工作流
        final_state = await self.graph.ainvoke(initial_state)
        
        # 构造输出
        return EnrichmentOutput(
            success=final_state.get("success", False),
            message=final_state.get("message", "未知错误"),
            data=final_state.get("final_data"),
            source=final_state.get("source", "unknown"),
            update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )


# ==========================================
# 便捷函数
# ==========================================
async def enrich_car_data(
    car_series_name: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    便捷函数：补充车型数据
    
    使用示例:
        result = await enrich_car_data("比亚迪秦PLUS")
        if result["success"]:
            print(f"数据已补充: {result['data']}")
    """
    agent = DataEnrichmentAgent()
    output = await agent.enrich(car_series_name, force_refresh)
    return output.dict()
