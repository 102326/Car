import json
from typing import List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# LangChain 相关导入
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from app.core.database import get_db
from app.models import CarBrand


# ==========================================
# 1. 定义 AI 返回的结构化模型
# ==========================================
class BrandInfoItem(BaseModel):
    """单个品牌的补全信息"""
    name_cn: str = Field(description="品牌的中文名称")
    name_en: str = Field(description="品牌的官方英文名称")
    country: str = Field(description="品牌所属的国家")

class BrandInfoList(BaseModel):
    """批量补全结果列表"""
    items: List[BrandInfoItem]

# ==========================================
# 2. AI 补全服务类
# ==========================================

class CarAICompletionService:
    def __init__(self):
        self._llm = None
        self._prompt = None
    
    def _ensure_initialized(self):
        """懒加载：只在第一次调用时初始化 Ollama"""
        if self._llm is None:
        # 初始化本地 Ollama 实例
            self._llm = ChatOllama(
            model="qwen2.5-coder:14b",
            base_url="http://localhost:11434",
            temperature=0,  # 购车数据需要严谨，设为 0
            format="json"  # 强制要求返回 JSON
        )

        # 定义 Prompt 模板
            self._prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一个专业的全球汽车产业专家。你需要根据提供的中文汽车品牌名称，补全它们的官方英文名称和所属国家。"),
            ("human",
             "请补全以下品牌的英文名和所属国家：{brand_names}\n\n注意：严格按 JSON 格式返回，格式如下：\n{{\"items\": [{{ \"name_cn\": \"...\", \"name_en\": \"...\", \"country\": \"...\" }}]}}")
        ])

    async def complete_brand_info(self, brand_names: List[str]) -> List[BrandInfoItem]:
        """调用 Ollama 进行补全"""
        if not brand_names:
            return []

        # 懒加载初始化
        self._ensure_initialized()

        # 详细日志：准备调用 AI
        print(f"\n{'='*60}")
        print(f"[AI 调用] 开始补全品牌信息")
        print(f"{'='*60}")
        print(f"待补全品牌: {', '.join(brand_names)}")
        print(f"调用模型: qwen2.5-coder:14b")
        print(f"API 地址: http://localhost:11434")

        # 构建链并调用
        chain = self._prompt | self._llm
        print(f"\n[AI 调用] 正在等待 Ollama 响应...")
        
        import time
        start_time = time.time()
        response = await chain.ainvoke({"brand_names": ", ".join(brand_names)})
        elapsed_time = time.time() - start_time
        
        print(f"[AI 调用] 响应耗时: {elapsed_time:.2f} 秒")
        print(f"[AI 调用] 原始响应长度: {len(response.content)} 字符")

        try:
            # 解析 AI 返回的 JSON 字符串
            parsed_data = json.loads(response.content)
            result_items = BrandInfoList(**parsed_data).items
            
            print(f"[AI 调用] 成功解析 {len(result_items)} 条结果")
            print(f"\n补全结果预览:")
            for item in result_items:
                print(f"  - {item.name_cn} -> {item.name_en} ({item.country})")
            print(f"{'='*60}\n")
            
            return result_items
        except Exception as e:
            print(f"[AI 调用] 解析失败: {e}")
            print(f"[AI 调用] 原始内容: {response.content[:500]}...")
            print(f"{'='*60}\n")
            return []


# ==========================================
# 3. FastAPI 接口实现
# ==========================================

router = APIRouter(prefix="/cartools")
ai_service = CarAICompletionService()


@router.post("/auto-complete-brands", summary="利用 AI 自动补全品牌缺失信息")
async def auto_complete_brands(
        batch_size: int = 10,
        session: AsyncSession = Depends(get_db)
):
    """
    逻辑：
    1. 从数据库找出 name_en 或 country 为空的品牌
    2. 调用 Ollama 进行识别
    3. 批量更新回数据库
    """
    # 1. 查询缺失数据的品牌
    print(f"\n[接口调用] /auto-complete-brands")
    print(f"[接口调用] batch_size = {batch_size}")
    
    stmt = select(CarBrand).where(
        (CarBrand.name_en == None) | (CarBrand.country == None)
    ).limit(batch_size)

    result = await session.execute(stmt)
    missing_brands = result.scalars().all()
    
    print(f"[数据库] 查询到 {len(missing_brands)} 条待补全记录")

    if not missing_brands:
        print(f"[接口调用] 没有需要补全的数据，返回\n")
        return {"message": "没有需要补全的品牌数据", "count": 0}

    names_to_query = [b.name for b in missing_brands]
    print(f"[数据库] 品牌列表: {', '.join(names_to_query[:5])}{'...' if len(names_to_query) > 5 else ''}")

    # 2. 调用 AI 补全
    completed_items = await ai_service.complete_brand_info(names_to_query)

    # 3. 构造更新映射
    update_count = 0
    print(f"\n[数据库] 开始更新数据库...")
    for item in completed_items:
        # 执行异步更新
        q = update(CarBrand).where(CarBrand.name == item.name_cn).values(
            name_en=item.name_en,
            country=item.country
        )
        await session.execute(q)
        update_count += 1

    await session.commit()
    print(f"[数据库] 成功更新 {update_count} 条记录")
    print(f"[接口调用] 任务完成\n")

    return {
        "message": "AI 补全任务完成",
        "processed_count": len(missing_brands),
        "updated_count": update_count,
        "details": completed_items
    }
