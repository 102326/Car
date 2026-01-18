# app/services/mongo_config_service.py
"""
MongoDB 详细配置查询服务
"""
import logging
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logger = logging.getLogger(__name__)


class MongoConfigService:
    """
    MongoDB 配置查询服务

    数据库: yiche_flexible
    集合: car_detailed_config (车型详细配置)
    """

    @classmethod
    def get_db(cls):
        """
        获取 MongoDB 数据库连接

        优先使用 connection_manager（FastAPI 环境）
        如果不可用，则创建独立连接（命令行环境）
        """
        try:
            # 优先使用全局连接管理器
            from app.core.connections import connection_manager
            mongo_db = connection_manager.get_mongo_db()
            return mongo_db
        except RuntimeError:
            # 降级：创建独立连接（命令行模式）
            logger.warning("[MongoDB] 使用独立连接（非 FastAPI 环境）")
            client = AsyncIOMotorClient(
                settings.MONGO_URL,
                serverSelectionTimeoutMS=5000
            )
            return client[settings.MONGO_DB_NAME]

    @classmethod
    async def query_car_config(
        cls,
        car_series_name: str,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询车型详细配置

        Args:
            car_series_name: 车系名称（如"比亚迪秦PLUS"）
            model_name: 具体车型名称（可选）

        Returns:
            {
                "success": bool,
                "data": {
                    "basic": {...},
                    "engine": {...},
                    "chassis": {...},
                    "safety": {...},
                    "comfort": {...},
                    "intelligence": {...}
                },
                "message": str
            }
        """
        try:
            db = cls.get_db()

            # 构造查询条件
            query = {
                "series_name": {"$regex": car_series_name, "$options": "i"}
            }

            if model_name:
                query["model_name"] = {
                    "$regex": model_name, "$options": "i"
                }

            # 查询 MongoDB
            collection = db.car_detailed_config
            result = await collection.find_one(query)

            if not result:
                logger.warning(
                    f"[MongoDB] 未找到配置: {car_series_name} "
                    f"{model_name or ''}"
                )
                return {
                    "success": False,
                    "data": {},
                    "message": f"未找到 {car_series_name} 的详细配置"
                }

            # 提取配置数据
            config_data = {
                "basic": result.get("basic_info", {}),
                "engine": result.get("engine_config", {}),
                "chassis": result.get("chassis_config", {}),
                "safety": result.get("safety_config", {}),
                "comfort": result.get("comfort_config", {}),
                "intelligence": result.get("intelligence_config", {})
            }

            logger.info(f"[MongoDB] 查询成功: {car_series_name}")

            return {
                "success": True,
                "data": config_data,
                "message": "查询成功"
            }

        except Exception as e:
            logger.error(f"[MongoDB] 查询失败: {e}")
            return {
                "success": False,
                "data": {},
                "message": f"查询失败: {str(e)}"
            }

    @classmethod
    async def query_car_specs(
        cls,
        car_series_name: str,
        spec_type: str = "all"
    ) -> Dict[str, Any]:
        """
        查询特定类型的配置参数

        Args:
            car_series_name: 车系名称
            spec_type: 配置类型
                (engine/chassis/safety/comfort/intelligence/all)

        Returns:
            配置信息
        """
        try:
            db = cls.get_db()
            collection = db.car_detailed_config

            query = {
                "series_name": {"$regex": car_series_name, "$options": "i"}
            }

            # 根据类型选择投影字段
            projection = {"_id": 0}
            if spec_type != "all":
                projection[f"{spec_type}_config"] = 1
                projection["series_name"] = 1
                projection["model_name"] = 1

            results = await collection.find(
                query, projection
            ).to_list(length=10)

            if not results:
                return {
                    "success": False,
                    "data": [],
                    "message": f"未找到 {car_series_name} 的配置信息"
                }

            return {
                "success": True,
                "data": results,
                "count": len(results),
                "message": f"找到 {len(results)} 个车型配置"
            }

        except Exception as e:
            logger.error(f"[MongoDB] 查询配置失败: {e}")
            return {
                "success": False,
                "data": [],
                "message": f"查询失败: {str(e)}"
            }

    @classmethod
    async def compare_configs(
        cls,
        car_series_list: List[str]
    ) -> Dict[str, Any]:
        """
        对比多个车型的配置

        Args:
            car_series_list: 车系名称列表（如["秦PLUS", "Model 3"]）

        Returns:
            对比结果
        """
        try:
            db = cls.get_db()
            collection = db.car_detailed_config

            comparison_data = []

            for series_name in car_series_list:
                query = {
                    "series_name": {"$regex": series_name, "$options": "i"}
                }
                result = await collection.find_one(query)

                if result:
                    comparison_data.append({
                        "series_name": result.get("series_name"),
                        "model_name": result.get("model_name"),
                        "basic": result.get("basic_info", {}),
                        "engine": result.get("engine_config", {}),
                        "safety": result.get("safety_config", {})
                    })

            return {
                "success": True,
                "data": comparison_data,
                "count": len(comparison_data),
                "message": f"成功对比 {len(comparison_data)} 个车型"
            }

        except Exception as e:
            logger.error(f"[MongoDB] 对比配置失败: {e}")
            return {
                "success": False,
                "data": [],
                "message": f"对比失败: {str(e)}"
            }


# ==========================================
# 便捷函数
# ==========================================
async def get_car_config(car_series_name: str) -> Dict[str, Any]:
    """
    便捷函数：查询车型详细配置

    使用示例:
        config = await get_car_config("比亚迪秦PLUS")
        print(config["data"]["engine"])  # 发动机配置
    """
    return await MongoConfigService.query_car_config(car_series_name)
