# app/utils/vision_helper.py
"""
视觉识别辅助工具（基于 minicpm-v）
"""
import base64
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class VisionHelper:
    """
    视觉识别助手
    
    使用 minicpm-v 多模态模型处理图像识别任务
    """
    
    def __init__(self):
        """初始化视觉模型"""
        try:
            self.model = ChatOllama(
                model="minicpm-v",
                base_url="http://localhost:11434",
                temperature=0.1  # 低温度，保证识别准确性
            )
            logger.info("✅ [Vision] minicpm-v 模型初始化成功")
        except Exception as e:
            logger.error(f"❌ [Vision] minicpm-v 模型初始化失败: {e}")
            self.model = None
    
    def _encode_image(self, image_path: str) -> str:
        """
        将图片编码为 base64
        
        Args:
            image_path: 图片路径
        
        Returns:
            base64 编码的图片数据
        """
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _create_vision_message(self, text: str, image_path: str) -> HumanMessage:
        """
        创建包含图片和文字的消息
        
        这是多模态模型的关键：将图片和文字组合成一个消息
        """
        image_b64 = self._encode_image(image_path)
        
        return HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": text
                },
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{image_b64}"
                }
            ]
        )
    
    async def recognize_car_brand(self, image_path: str) -> Dict[str, Any]:
        """
        识别车辆品牌和车型
        
        Args:
            image_path: 车辆图片路径
        
        Returns:
            {
                "brand": "比亚迪",
                "series": "秦PLUS",
                "confidence": 0.95,
                "description": "..."
            }
        """
        if not self.model:
            return {"error": "视觉模型未初始化"}
        
        try:
            prompt = """
请识别这辆车的品牌和车型，并按以下格式回答（JSON格式）：
{
    "brand": "品牌名称",
    "series": "车系名称（如果能识别）",
    "confidence": 0.0-1.0,
    "description": "详细描述外观特征"
}
"""
            
            message = self._create_vision_message(prompt, image_path)
            response = await self.model.ainvoke([message])
            
            # 解析响应
            import json
            result = json.loads(response.content)
            
            logger.info(f"[Vision] 识别结果: {result['brand']} {result.get('series', '')}")
            
            return result
            
        except Exception as e:
            logger.error(f"[Vision] 识别失败: {e}")
            return {"error": str(e)}
    
    async def analyze_car_condition(self, image_path: str) -> Dict[str, Any]:
        """
        分析二手车车况（用于估价）
        
        Args:
            image_path: 车辆图片路径
        
        Returns:
            {
                "scratches": ["前保险杠右侧有划痕"],
                "dents": [],
                "paint_condition": "良好",
                "lights_condition": "完好",
                "tire_wear": "30%",
                "overall_score": 7.5,
                "grade": "良"
            }
        """
        if not self.model:
            return {"error": "视觉模型未初始化"}
        
        try:
            prompt = """
请详细分析这辆车的外观车况，包括：
1. 划痕和凹陷位置
2. 车漆状况
3. 车灯状况
4. 轮胎磨损程度
5. 综合评分（0-10分）
6. 车况等级（优/良/中/差）

请按 JSON 格式回答：
{
    "scratches": ["划痕位置列表"],
    "dents": ["凹陷位置列表"],
    "paint_condition": "车漆状况描述",
    "lights_condition": "车灯状况",
    "tire_wear": "磨损百分比",
    "overall_score": 7.5,
    "grade": "良"
}
"""
            
            message = self._create_vision_message(prompt, image_path)
            response = await self.model.ainvoke([message])
            
            # 解析响应
            import json
            result = json.loads(response.content)
            
            logger.info(f"[Vision] 车况评估: {result['grade']} ({result['overall_score']}/10)")
            
            return result
            
        except Exception as e:
            logger.error(f"[Vision] 车况分析失败: {e}")
            return {"error": str(e)}
    
    async def ocr_vehicle_license(self, image_path: str) -> Dict[str, Any]:
        """
        识别行驶证信息（OCR）
        
        Args:
            image_path: 行驶证照片路径
        
        Returns:
            {
                "plate_number": "京A12345",
                "owner": "张三",
                "brand": "比亚迪",
                "model": "秦PLUS DM-i",
                "register_date": "2023-06-15",
                "vin": "LGXC16DB8N0123456"
            }
        """
        if not self.model:
            return {"error": "视觉模型未初始化"}
        
        try:
            prompt = """
这是一张行驶证照片，请提取以下信息：
1. 车牌号
2. 所有人
3. 品牌型号
4. 注册日期
5. 车辆识别代号（VIN）

请按 JSON 格式回答：
{
    "plate_number": "车牌号",
    "owner": "所有人",
    "brand": "品牌",
    "model": "型号",
    "register_date": "注册日期",
    "vin": "车辆识别代号"
}
"""
            
            message = self._create_vision_message(prompt, image_path)
            response = await self.model.ainvoke([message])
            
            # 解析响应
            import json
            result = json.loads(response.content)
            
            logger.info(f"[Vision] OCR 识别成功: {result['plate_number']}")
            
            return result
            
        except Exception as e:
            logger.error(f"[Vision] OCR 识别失败: {e}")
            return {"error": str(e)}


# ==========================================
# 单例实例
# ==========================================
vision_helper = VisionHelper()


# ==========================================
# 便捷函数
# ==========================================
async def recognize_car(image_path: str) -> Dict[str, Any]:
    """
    便捷函数：识别车辆品牌和车型
    
    使用示例:
        result = await recognize_car("car.jpg")
        print(f"品牌: {result['brand']}, 车型: {result['series']}")
    """
    return await vision_helper.recognize_car_brand(image_path)


async def analyze_condition(image_path: str) -> Dict[str, Any]:
    """
    便捷函数：分析二手车车况
    
    使用示例:
        result = await analyze_condition("used_car.jpg")
        print(f"车况等级: {result['grade']}, 得分: {result['overall_score']}")
    """
    return await vision_helper.analyze_car_condition(image_path)


async def extract_license_info(image_path: str) -> Dict[str, Any]:
    """
    便捷函数：提取行驶证信息
    
    使用示例:
        result = await extract_license_info("license.jpg")
        print(f"车牌: {result['plate_number']}, VIN: {result['vin']}")
    """
    return await vision_helper.ocr_vehicle_license(image_path)
