# app/services/trade_service.py
"""
交易服务：处理试驾预约、二手车估价、订单查询等
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.car import CarDealer
from app.models.trade import TradeOrder
from app.core.database import get_async_session

logger = logging.getLogger(__name__)


class TradeService:
    """
    交易服务
    
    功能：
    - 试驾预约
    - 二手车估价
    - 订单查询
    - 经销商推荐
    """
    
    @staticmethod
    async def handle_request(
        query: str,
        user_id: Optional[int] = None,
        user_city: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理交易相关请求
        
        Args:
            query: 用户查询
            user_id: 用户ID
            user_city: 用户城市
        
        Returns:
            交易信息字典
        """
        # 识别请求类型
        if "试驾" in query or "预约" in query:
            return await TradeService.handle_test_drive(query, user_city)
        elif "估价" in query or "置换" in query or "卖车" in query:
            return await TradeService.handle_trade_in(query)
        elif "订单" in query or "订金" in query:
            return await TradeService.handle_order_query(user_id)
        elif "贷款" in query or "金融" in query or "分期" in query:
            return await TradeService.handle_finance(query)
        else:
            return {
                "type": "unknown",
                "message": "抱歉，我不太理解您的需求，请问您是想试驾、估价还是查询订单？"
            }
    
    @staticmethod
    async def handle_test_drive(query: str, user_city: Optional[str] = None) -> Dict[str, Any]:
        """
        处理试驾预约
        
        Args:
            query: 用户查询
            user_city: 用户城市
        
        Returns:
            经销商列表
        """
        try:
            # 从查询中提取车系名称
            from app.agents.nodes import _extract_car_series_from_question
            car_series_name = _extract_car_series_from_question(query)
            
            # 查询经销商
            dealers = await TradeService.find_nearby_dealers(
                car_series_name=car_series_name,
                city=user_city
            )
            
            if dealers:
                return {
                    "type": "test_drive",
                    "message": f"已为您推荐 {len(dealers)} 家附近的经销商",
                    "car_series": car_series_name,
                    "dealers": dealers
                }
            else:
                return {
                    "type": "test_drive",
                    "message": "抱歉，暂未找到附近的经销商，请稍后再试或联系客服",
                    "car_series": car_series_name,
                    "dealers": []
                }
                
        except Exception as e:
            logger.error(f"[TradeService] 试驾预约处理失败: {e}")
            return {
                "type": "test_drive",
                "message": f"处理失败: {str(e)}",
                "dealers": []
            }
    
    @staticmethod
    async def find_nearby_dealers(
        car_series_name: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        查询附近的经销商
        
        Args:
            car_series_name: 车系名称（用于匹配品牌）
            city: 城市
            limit: 返回数量
        
        Returns:
            经销商列表
        """
        try:
            async for session in get_async_session():
                stmt = select(CarDealer)
                
                # 城市过滤
                if city:
                    stmt = stmt.where(CarDealer.city == city)
                
                # 限制数量
                stmt = stmt.limit(limit)
                
                result = await session.execute(stmt)
                dealers = result.scalars().all()
                
                # 转换为字典
                dealer_list = []
                for dealer in dealers:
                    dealer_list.append({
                        "id": dealer.id,
                        "name": dealer.name,
                        "city": dealer.city,
                        "province": dealer.province,
                        "phone": dealer.phone,
                        "address": f"{dealer.province}{dealer.city}",
                        "latitude": float(dealer.latitude) if dealer.latitude else None,
                        "longitude": float(dealer.longitude) if dealer.longitude else None
                    })
                
                logger.info(f"[TradeService] 找到 {len(dealer_list)} 家经销商")
                return dealer_list
                
        except Exception as e:
            logger.error(f"[TradeService] 查询经销商失败: {e}")
            return []
    
    @staticmethod
    async def handle_trade_in(query: str) -> Dict[str, Any]:
        """
        处理二手车估价
        
        Args:
            query: 用户查询
        
        Returns:
            估价信息
        """
        return {
            "type": "trade_in",
            "message": "二手车估价需要提供以下信息，请告诉我：",
            "required_info": {
                "brand": "品牌（如：比亚迪）",
                "series": "车系（如：秦PLUS）",
                "year": "年款（如：2023年）",
                "mileage": "行驶里程（如：3万公里）",
                "condition": "车况（优/良/中/差）",
                "city": "所在城市"
            },
            "tips": "您也可以上传车辆照片，我们的AI会自动识别车况"
        }
    
    @staticmethod
    async def handle_order_query(user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        查询订单
        
        Args:
            user_id: 用户ID
        
        Returns:
            订单列表
        """
        if not user_id:
            return {
                "type": "order",
                "message": "请先登录后查询订单",
                "orders": []
            }
        
        try:
            async for session in get_async_session():
                stmt = select(TradeOrder).where(
                    TradeOrder.user_id == user_id
                ).order_by(TradeOrder.created_at.desc()).limit(10)
                
                result = await session.execute(stmt)
                orders = result.scalars().all()
                
                order_list = []
                for order in orders:
                    order_list.append({
                        "id": order.id,
                        "order_type": order.order_type,
                        "total_amount": float(order.total_amount),
                        "status": order.status,
                        "created_at": order.created_at.isoformat()
                    })
                
                return {
                    "type": "order",
                    "message": f"找到 {len(order_list)} 个订单",
                    "orders": order_list
                }
                
        except Exception as e:
            logger.error(f"[TradeService] 查询订单失败: {e}")
            return {
                "type": "order",
                "message": f"查询失败: {str(e)}",
                "orders": []
            }
    
    @staticmethod
    async def handle_finance(query: str) -> Dict[str, Any]:
        """
        处理金融方案查询
        
        Args:
            query: 用户查询
        
        Returns:
            金融方案信息
        """
        return {
            "type": "finance",
            "message": "我们提供多种金融方案，请告诉我您的购车预算和期望的还款期限",
            "plans": [
                {
                    "name": "零首付方案",
                    "down_payment": "0%",
                    "term": "36期",
                    "interest_rate": "5.5%",
                    "note": "需要满足一定的信用条件"
                },
                {
                    "name": "低息方案",
                    "down_payment": "30%",
                    "term": "24期",
                    "interest_rate": "3.5%",
                    "note": "推荐方案"
                },
                {
                    "name": "厂家金融",
                    "down_payment": "20%",
                    "term": "36期",
                    "interest_rate": "0%",
                    "note": "部分车型限时优惠"
                }
            ],
            "tips": "具体方案需要根据您的信用情况和车型确定，建议联系经销商详细咨询"
        }
