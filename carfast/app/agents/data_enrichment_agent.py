# app/agents/data_enrichment_agent.py
"""
数据补充子 Agent
负责在知识库检索失败时，调用外部API或数据库实时查询汽车信息
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.car import CarSeries, CarModel
from app.core.database import AsyncSessionLocal


class DataEnrichmentAgent:
    """
    数据补充专家 Agent
    
    功能:
        1. 从数据库查询最新车型信息
        2. 调用外部API获取实时数据（如优惠、补贴）
        3. 结构化数据返回给主Agent
    """
    
    @staticmethod
    async def query(
        query: str,
        user_profile: Dict[str, Any],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        主查询接口
        
        Args:
            query: 用户查询内容
            user_profile: 用户画像
            db: 数据库会话（可选）
        
        Returns:
            {
                "success": bool,
                "data": {...},
                "message": str,
                "update_time": str
            }
        """
        # 解析查询类型
        query_type = DataEnrichmentAgent._parse_query_type(query)
        
        # 提取车系名称
        car_series_name = DataEnrichmentAgent._extract_car_series(query)
        
        if not car_series_name:
            return {
                "success": False,
                "data": {},
                "message": "无法识别车型名称，请提供更具体的信息",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # 根据查询类型执行不同逻辑
        if query_type == "price":
            return await DataEnrichmentAgent._query_price(car_series_name, user_profile, db)
        elif query_type == "config":
            return await DataEnrichmentAgent._query_config(car_series_name, db)
        elif query_type == "subsidy":
            return await DataEnrichmentAgent._query_subsidy(car_series_name, user_profile)
        elif query_type == "dealer":
            return await DataEnrichmentAgent._query_dealer(car_series_name, user_profile, db)
        else:
            # 默认返回综合信息
            return await DataEnrichmentAgent._query_comprehensive(car_series_name, user_profile, db)
    
    @staticmethod
    def _parse_query_type(query: str) -> str:
        """解析查询类型"""
        if any(keyword in query for keyword in ["价格", "多少钱", "报价", "优惠"]):
            return "price"
        elif any(keyword in query for keyword in ["配置", "参数", "配置表"]):
            return "config"
        elif any(keyword in query for keyword in ["补贴", "政策", "免税"]):
            return "subsidy"
        elif any(keyword in query for keyword in ["4S店", "经销商", "试驾", "门店"]):
            return "dealer"
        else:
            return "comprehensive"
    
    @staticmethod
    def _extract_car_series(query: str) -> Optional[str]:
        """
        从查询中提取车系名称
        
        使用正则表达式 + 关键词库匹配（已优化）
        """
        import re
        
        known_series = [
            "秦PLUS", "秦Plus", "秦plus", "秦",
            "汉", "唐", "宋PLUS", "海豹", "海鸥", "元PLUS",
            "Model 3", "Model Y", "Model S", "Model X",
            "理想L6", "理想L7", "理想L8", "理想L9",
            "小鹏P7", "小鹏G9", "小鹏G6",
            "蔚来ET5", "蔚来ES6", "蔚来ET7",
            "奥迪A4L", "奥迪A6L", "宝马3系", "宝马5系",
            "奔驰C级", "奔驰E级", "本田CR-V", "大众途观L"
        ]
        known_series.sort(key=len, reverse=True)
        
        query_lower = query.lower()
        for series in known_series:
            if series.lower() in query_lower:
                return series
        
        # 正则匹配
        patterns = [r'[A-Z]+\d+[A-Z]*', r'[\u4e00-\u9fff]+(?:PLUS|Plus)?']
        for pattern in patterns:
            matches = re.findall(pattern, query)
            if matches:
                return max(matches, key=len)
        
        return None
    
    @staticmethod
    async def _query_price(
        car_series_name: str,
        user_profile: Dict[str, Any],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """查询价格信息"""
        try:
            # 正确用法：直接创建会话（如果未传入）
            if db is None:
                async with AsyncSessionLocal() as session:
                    # 查询车系
                    stmt = select(CarSeries).where(CarSeries.name.like(f"%{car_series_name}%"))
                    result = await session.execute(stmt)
                    car_series = result.scalar_one_or_none()
                    
                    if not car_series:
                        return {
                            "success": False,
                            "data": {},
                            "message": f"未找到车系: {car_series_name}",
                            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    
                    # 查询该车系下的所有车型
                    stmt = select(CarModel).where(
                        CarModel.series_id == car_series.id,
                        CarModel.status == 1  # 在售
                    )
                    result = await session.execute(stmt)
                    models = result.scalars().all()
                    
                    # 构造返回数据
                    models_data = [
                        {
                            "name": model.name,
                            "price_guidance": float(model.price_guidance),
                            "year": model.year,
                            "status": "在售" if model.status == 1 else "停售",
                            "extra_tags": model.extra_tags or {}
                        }
                        for model in models
                    ]
            
            return {
                "success": True,
                "data": {
                    "car_series": car_series.name,
                    "brand": car_series.brand.name if car_series.brand else "未知",
                    "energy_type": car_series.energy_type,
                    "price_range": f"{car_series.min_price_guidance}-{car_series.max_price_guidance}万",
                    "models": models_data,
                    "city_policy": f"{user_profile.get('city', '本地')}地区政策待查询"
                },
                "message": "成功获取最新价格信息",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"[DataEnrichmentAgent] 查询价格失败: {e}")
            return {
                "success": False,
                "data": {},
                "message": f"查询失败: {str(e)}",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    @staticmethod
    async def _query_config(car_series_name: str, db: AsyncSession = None) -> Dict[str, Any]:
        """查询配置信息（从MongoDB获取详细参数）"""
        try:
            from app.services.mongo_config_service import MongoConfigService
            
            result = await MongoConfigService.query_car_config(car_series_name)
            
            if result["success"]:
                return {
                    "success": True,
                    "data": {"car_series": car_series_name, "config": result["data"]},
                    "message": "成功获取详细配置",
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    "success": False,
                    "data": {},
                    "message": result["message"],
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            return {
                "success": False,
                "data": {},
                "message": f"配置查询失败: {str(e)}",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    @staticmethod
    async def _query_subsidy(
        car_series_name: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """查询补贴政策"""
        try:
            from app.services.policy_service import PolicyService
            
            city = user_profile.get("city", "未知")
            energy_type = user_profile.get("preferences", {}).get("energy_type", "未知")
            
            result = await PolicyService.query_policy(
                car_series_name=car_series_name,
                energy_type=energy_type,
                city=city,
                price=user_profile.get("budget_max")
            )
            
            return {
                "success": result["success"],
                "data": result if result["success"] else {},
                "message": result["message"],
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            city = user_profile.get("city", "未知")
            return {
                "success": False,
                "data": {},
                "message": f"政策查询失败: {str(e)}",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    @staticmethod
    async def _query_dealer(
        car_series_name: str,
        user_profile: Dict[str, Any],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """查询经销商信息"""
        try:
            from app.services.trade_service import TradeService
            
            city = user_profile.get("city")
            dealers = await TradeService.find_nearby_dealers(
                car_series_name=car_series_name,
                city=city,
                limit=5
            )
            
            return {
                "success": True,
                "data": {
                    "car_series": car_series_name,
                    "city": city or "全国",
                    "dealers": dealers
                },
                "message": f"已为您推荐 {len(dealers)} 家附近的经销商",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            city = user_profile.get("city", "未知")
            return {
                "success": False,
                "data": {},
                "message": f"经销商查询失败: {str(e)}",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    @staticmethod
    async def _query_comprehensive(
        car_series_name: str,
        user_profile: Dict[str, Any],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """查询综合信息（价格+配置+补贴）"""
        price_info = await DataEnrichmentAgent._query_price(car_series_name, user_profile, db)
        subsidy_info = await DataEnrichmentAgent._query_subsidy(car_series_name, user_profile)
        
        if not price_info["success"]:
            return price_info
        
        return {
            "success": True,
            "data": {
                **price_info["data"],
                "subsidies": subsidy_info["data"]["subsidies"]
            },
            "message": "成功获取综合信息",
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


# ==========================================
# 测试代码
# ==========================================
if __name__ == "__main__":
    import asyncio
    
    async def test_enrichment():
        # 测试查询
        result = await DataEnrichmentAgent.query(
            query="比亚迪秦PLUS的价格是多少",
            user_profile={"city": "北京", "budget_min": 10, "budget_max": 15}
        )
        
        print("查询结果:")
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    asyncio.run(test_enrichment())
