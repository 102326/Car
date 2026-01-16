# app/services/policy_service.py
"""
政策补贴服务
参考: https://github.com/baifachuan/policy_pyspider.git
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PolicyService:
    """
    政策补贴查询服务
    
    功能：
    - 查询新能源补贴政策
    - 查询地方购车补贴
    - 查询购置税减免政策
    """
    
    # 国家级政策（相对稳定）
    NATIONAL_POLICIES = {
        "新能源免购置税": {
            "name": "新能源汽车免征车辆购置税",
            "type": "tax_exemption",
            "amount": "按车价10%计算",
            "valid_until": "2027-12-31",
            "applicable": ["纯电动", "插电式混合动力", "燃料电池"],
            "note": "购置税 = 车价 / 1.13 * 10%，免征可节省约1-3万元"
        },
        "新能源车船税": {
            "name": "新能源汽车免征车船税",
            "type": "tax_exemption",
            "amount": "全免",
            "valid_until": "长期有效",
            "applicable": ["纯电动", "插电式混合动力", "燃料电池"],
            "note": "每年节省约300-600元"
        }
    }
    
    # 地方政策（需要定期更新）
    CITY_POLICIES = {
        "上海": [
            {
                "name": "上海新能源汽车专用牌照额度",
                "type": "license_plate",
                "amount": "免费（价值约10万元）",
                "valid_until": "2026-12-31",
                "applicable": ["纯电动", "插电式混合动力"],
                "conditions": ["上海户籍或居住证", "名下无沪牌车辆"],
                "note": "燃油车牌照需要拍卖，成交价约10万元"
            },
            {
                "name": "上海新能源汽车充电补贴",
                "type": "subsidy",
                "amount": "5000元",
                "valid_until": "2026-06-30",
                "applicable": ["纯电动"],
                "note": "购车后申请，用于充电桩安装"
            }
        ],
        "北京": [
            {
                "name": "北京新能源指标",
                "type": "license_plate",
                "amount": "免费（需摇号）",
                "valid_until": "长期有效",
                "applicable": ["纯电动"],
                "conditions": ["北京户籍或居住证", "连续5年社保"],
                "note": "纯电动车单独摇号，中签率较高"
            }
        ],
        "深圳": [
            {
                "name": "深圳新能源汽车综合补贴",
                "type": "subsidy",
                "amount": "10000元",
                "valid_until": "2026-12-31",
                "applicable": ["纯电动", "插电式混合动力"],
                "note": "购车后6个月内申请"
            }
        ],
        "广州": [
            {
                "name": "广州新能源汽车购车补贴",
                "type": "subsidy",
                "amount": "8000元",
                "valid_until": "2026-06-30",
                "applicable": ["纯电动"],
                "note": "限额1万个名额"
            }
        ],
        "杭州": [
            {
                "name": "杭州新能源汽车补贴",
                "type": "subsidy",
                "amount": "6000元",
                "valid_until": "2026-12-31",
                "applicable": ["纯电动", "插电式混合动力"],
                "note": "需要在杭州上牌"
            }
        ]
    }
    
    @staticmethod
    async def query_policy(
        car_series_name: str,
        energy_type: str,
        city: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        查询购车补贴政策
        
        Args:
            car_series_name: 车系名称
            energy_type: 能源类型（纯电/插电式混合动力/燃油）
            city: 城市
            price: 车价（万元）
        
        Returns:
            {
                "success": bool,
                "car_series": str,
                "energy_type": str,
                "city": str,
                "policies": [...],
                "total_benefit": float,
                "message": str
            }
        """
        try:
            applicable_policies = []
            total_benefit = 0.0
            
            # 1. 国家级政策
            for policy_key, policy in PolicyService.NATIONAL_POLICIES.items():
                if energy_type in policy["applicable"]:
                    policy_copy = policy.copy()
                    
                    # 计算购置税减免金额
                    if policy["type"] == "tax_exemption" and price:
                        if "购置税" in policy["name"]:
                            tax_amount = price * 10000 / 1.13 * 0.1 / 10000  # 转换为万元
                            policy_copy["estimated_amount"] = round(tax_amount, 2)
                            total_benefit += tax_amount
                    
                    applicable_policies.append(policy_copy)
            
            # 2. 地方政策
            if city and city in PolicyService.CITY_POLICIES:
                for policy in PolicyService.CITY_POLICIES[city]:
                    if energy_type in policy["applicable"]:
                        policy_copy = policy.copy()
                        
                        # 提取补贴金额
                        if policy["type"] == "subsidy":
                            amount_str = policy["amount"]
                            import re
                            amount_match = re.search(r'(\d+)', amount_str)
                            if amount_match:
                                amount = float(amount_match.group(1)) / 10000  # 转换为万元
                                policy_copy["estimated_amount"] = amount
                                total_benefit += amount
                        
                        applicable_policies.append(policy_copy)
            
            logger.info(f"[Policy] 查询成功: {city or '全国'} - {energy_type} - {len(applicable_policies)} 项政策")
            
            return {
                "success": True,
                "car_series": car_series_name,
                "energy_type": energy_type,
                "city": city or "全国",
                "policies": applicable_policies,
                "total_benefit": round(total_benefit, 2),
                "message": f"找到 {len(applicable_policies)} 项适用政策，预计可节省约 {round(total_benefit, 2)} 万元",
                "update_time": datetime.now().strftime("%Y-%m-%d")
            }
            
        except Exception as e:
            logger.error(f"[Policy] 查询失败: {e}")
            return {
                "success": False,
                "message": f"查询失败: {str(e)}",
                "policies": []
            }
    
    @staticmethod
    async def get_city_policies(city: str) -> List[Dict[str, Any]]:
        """
        获取指定城市的所有政策
        
        Args:
            city: 城市名称
        
        Returns:
            政策列表
        """
        policies = []
        
        # 国家政策
        for policy in PolicyService.NATIONAL_POLICIES.values():
            policies.append({**policy, "level": "国家级"})
        
        # 地方政策
        if city in PolicyService.CITY_POLICIES:
            for policy in PolicyService.CITY_POLICIES[city]:
                policies.append({**policy, "level": "地方级"})
        
        return policies
    
    @staticmethod
    def add_city_policy(city: str, policy: Dict[str, Any]):
        """
        动态添加城市政策（用于管理后台）
        
        Args:
            city: 城市名称
            policy: 政策信息
        """
        if city not in PolicyService.CITY_POLICIES:
            PolicyService.CITY_POLICIES[city] = []
        
        PolicyService.CITY_POLICIES[city].append(policy)
        logger.info(f"[Policy] 添加 {city} 政策: {policy['name']}")
