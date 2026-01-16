# app/services/hybrid_search_service.py
"""
混合检索服务：ES 关键字检索 + Milvus 向量检索
"""
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.model_factory import ModelFactory, ModelType, embedding_model, reranker_model


logger = logging.getLogger(__name__)


# ==========================================
# Pydantic Schemas
# ==========================================
class ESFilter(BaseModel):
    """ES 结构化过滤条件"""
    city: Optional[str] = Field(None, description="城市（用于本地化，如'上海'）")
    price_min: Optional[float] = Field(None, description="最低价格（万元）")
    price_max: Optional[float] = Field(None, description="最高价格（万元）")
    energy_type: Optional[str] = Field(None, description="能源类型（纯电/插电式混合动力/燃油/油电混合）")
    brand_name: Optional[str] = Field(None, description="品牌名称（如：比亚迪、奥迪）")
    series_level: Optional[str] = Field(None, description="车型级别（紧凑型车/中型车/SUV/MPV）")
    year: Optional[str] = Field(None, description="年款（如：2026）")
    status: Optional[int] = Field(1, description="状态（1=在售, 0=停售, 2=未上市）")


class HybridSearchQuery(BaseModel):
    """混合检索查询"""
    es_filter: ESFilter = Field(..., description="ES 结构化过滤条件")
    vector_query: str = Field(..., description="向量检索的语义查询文本")
    original_query: str = Field(..., description="原始用户查询")


class SearchResult(BaseModel):
    """检索结果"""
    id: int
    name: str
    brand_name: str
    series_name: str
    price: float
    energy_type: str
    series_level: str
    score: float  # 综合得分
    source: str  # "es" / "vector" / "hybrid"
    tags_text: Optional[str] = None


# ==========================================
# System Prompt for Query Parsing
# ==========================================
QUERY_PARSING_PROMPT = """
你是一个高级检索策略生成器，负责将用户的自然语言查询转换为结构化的检索指令。

## 背景
我们的汽车检索系统使用混合检索策略：
1. **ES 关键字检索**：擅长精确匹配硬性条件（价格、品牌、能源类型等）
2. **Milvus 向量检索**：擅长语义理解软性需求（舒适性、适合场景、驾驶感受等）

## ES 字段映射（参考）
- `brand_name`: 品牌（keyword，精确匹配）
  示例：比亚迪、奥迪、宝马、特斯拉、理想汽车、蔚来汽车
  
- `series_name`: 车系（keyword）
  示例：秦PLUS、汉、Model 3、理想L6
  
- `series_level`: 车型级别（keyword）
  示例：紧凑型车、中型车、SUV、MPV、紧凑型SUV、中型SUV
  
- `energy_type`: 能源类型（keyword）
  示例：纯电、插电式混合动力、燃油、油电混合
  
- `price`: 价格（double，单位：万元）
  支持范围查询：price >= min AND price <= max
  
- `year`: 年款（keyword）
  示例：2026、2025、2024
  
- `status`: 状态（integer）
  1=在售, 0=停售, 2=未上市
  
- `tags_text`: 标签文本（text，支持全文检索）
  示例：包含充电桩、免购置税、智能驾驶、L2辅助驾驶

## 用户查询
{user_query}

## 任务
分析用户查询，提取两部分信息：

### 1. ES Filter（硬性约束条件）
提取所有可以明确判断的条件，包括：
- **价格区间**：如"20万左右" -> price_min: 18, price_max: 22
  - "X万以内" -> price_max: X
  - "X-Y万" -> price_min: X, price_max: Y
  - "不超过X万" -> price_max: X
  
- **品牌**：如"比亚迪"、"奥迪"、"理想"
  注意：需要识别品牌全称（"理想" -> "理想汽车"）
  
- **能源类型**：
  - "纯电"/"电动"/"EV" -> "纯电"
  - "插混"/"PHEV"/"DM-i" -> "插电式混合动力"
  - "油电混动"/"HEV" -> "油电混合"
  - "汽油"/"燃油" -> "燃油"
  
- **车型级别**：
  - "SUV" -> "SUV"（如果未明确是紧凑型还是中型，只写"SUV"）
  - "轿车"/"sedan" -> "紧凑型车"或"中型车"（根据价格判断）
  - "MPV" -> "MPV"
  
- **年款**：如"2026款"、"最新款" -> year: "2026"

- **城市**：如"上海"、"北京"（用于本地化查询，非ES字段，但需提取）

**重要规则**：
- 如果用户未明确提及某个条件，**不要包含该字段**
- 价格范围允许一定弹性：如"20万左右" -> [18, 22]
- 默认只查询在售车型（status=1），除非用户明确要求停售/未上市

### 2. Vector Query（软性语义描述）
提取所有形容词、场景描述、驾驶感受等隐性需求，用于向量检索：
- **使用场景**：家用、商务、越野、露营、通勤、长途
- **舒适性**：舒适、豪华、静音、悬挂软硬、座椅材质
- **性能**：动力强、省油、加速快、底盘扎实、操控好
- **空间**：空间大、7座、后排宽敞、后备箱大
- **适用人群**：带孩子、老人、年轻人、女性
- **外观**：时尚、运动、商务、稳重
- **配置**：智能驾驶、大屏、天窗、氛围灯

**处理方式**：
- 将所有软性描述提取出来，用空格分隔
- 去除冗余词汇（的、了、吗、吧等）
- 保留核心关键词和短语

## 输出格式（严格JSON）
{{
  "es_filter": {{
    "city": "城市名称或null",
    "price_min": 最低价或null,
    "price_max": 最高价或null,
    "energy_type": "能源类型或null",
    "brand_name": "品牌或null",
    "series_level": "级别或null",
    "year": "年款或null",
    "status": 1
  }},
  "vector_query": "软性描述关键词（空格分隔）",
  "original_query": "{user_query}"
}}

## 示例1
**用户查询**: "我想在上海买个20万左右的纯电SUV，最好是比亚迪的，要适合带孩子，舒适性好。"

**输出**:
{{
  "es_filter": {{
    "city": "上海",
    "price_min": 18.0,
    "price_max": 22.0,
    "energy_type": "纯电",
    "brand_name": "比亚迪",
    "series_level": "SUV",
    "year": null,
    "status": 1
  }},
  "vector_query": "适合带孩子 家庭用车 舒适性好 空间大 悬挂舒适 静音",
  "original_query": "我想在上海买个20万左右的纯电SUV，最好是比亚迪的，要适合带孩子，舒适性好。"
}}

## 示例2
**用户查询**: "30万以内，动力强劲，底盘扎实，操控好的车有哪些"

**输出**:
{{
  "es_filter": {{
    "city": null,
    "price_min": null,
    "price_max": 30.0,
    "energy_type": null,
    "brand_name": null,
    "series_level": null,
    "year": null,
    "status": 1
  }},
  "vector_query": "动力强劲 底盘扎实 操控好 运动 驾驶感受佳",
  "original_query": "30万以内，动力强劲，底盘扎实，操控好的车有哪些"
}}

## 示例3
**用户查询**: "比亚迪秦PLUS怎么样"

**输出**:
{{
  "es_filter": {{
    "city": null,
    "price_min": null,
    "price_max": null,
    "energy_type": null,
    "brand_name": "比亚迪",
    "series_level": null,
    "year": null,
    "status": 1
  }},
  "vector_query": "秦PLUS 车型评价 优缺点 用户口碑",
  "original_query": "比亚迪秦PLUS怎么样"
}}

## 注意事项
1. 价格单位统一为"万元"（如119800元需转换为11.98万）
2. 品牌名称需要标准化：
   - "理想" -> "理想汽车"
   - "小鹏" -> "小鹏汽车"
   - "蔚来" -> "蔚来汽车"
   - "比亚迪"、"奥迪"、"宝马" 等保持不变
3. 如果查询非常简单（如"推荐一辆车"），es_filter 大部分字段为 null，vector_query 也简短
4. 严格按照 JSON 格式输出，不要添加任何额外的文字说明

现在，请解析用户查询：
"""


# ==========================================
# Query Parser (查询解析器)
# ==========================================
class QueryParser:
    """
    查询解析器：将自然语言转换为结构化检索指令
    """
    
    @staticmethod
    async def parse(user_query: str) -> HybridSearchQuery:
        """
        解析用户查询
        
        Args:
            user_query: 用户的自然语言查询
        
        Returns:
            HybridSearchQuery
        """
        try:
            # 使用"大脑"模型进行查询解析（复杂推理任务）
            llm = ModelFactory.get_brain_model(temperature=0.1)
            
            prompt = ChatPromptTemplate.from_template(QUERY_PARSING_PROMPT)
            chain = prompt | llm | StrOutputParser()
            
            result = await chain.ainvoke({"user_query": user_query})
            
            # 解析 JSON
            parsed = json.loads(result)
            
            # 构造 Pydantic 模型
            es_filter = ESFilter(**parsed.get("es_filter", {}))
            
            hybrid_query = HybridSearchQuery(
                es_filter=es_filter,
                vector_query=parsed.get("vector_query", ""),
                original_query=parsed.get("original_query", user_query)
            )
            
            logger.info(f"[QueryParser] 解析成功:")
            logger.info(f"  - ES Filter: {es_filter.dict(exclude_none=True)}")
            logger.info(f"  - Vector Query: {hybrid_query.vector_query}")
            
            return hybrid_query
            
        except json.JSONDecodeError as e:
            logger.error(f"[QueryParser] JSON 解析失败: {e}")
            logger.error(f"LLM 输出: {result}")
            
            # 降级：使用简单解析
            return QueryParser._fallback_parse(user_query)
            
        except Exception as e:
            logger.error(f"[QueryParser] 解析异常: {e}")
            return QueryParser._fallback_parse(user_query)
    
    @staticmethod
    def _fallback_parse(user_query: str) -> HybridSearchQuery:
        """降级解析：简单的关键词提取"""
        logger.warning("[QueryParser] 使用降级解析")
        
        # 简单的规则匹配
        es_filter = ESFilter()
        
        # 提取品牌
        brands = ["比亚迪", "奥迪", "宝马", "奔驰", "特斯拉", "理想汽车", "小鹏汽车", "蔚来汽车"]
        for brand in brands:
            if brand in user_query or brand.replace("汽车", "") in user_query:
                es_filter.brand_name = brand
                break
        
        # 提取价格
        import re
        price_pattern = r'(\d+)万'
        matches = re.findall(price_pattern, user_query)
        if matches:
            price = float(matches[0])
            if "以内" in user_query or "不超过" in user_query:
                es_filter.price_max = price
            else:
                es_filter.price_min = price * 0.9
                es_filter.price_max = price * 1.1
        
        # 提取能源类型
        if "纯电" in user_query or "电动" in user_query:
            es_filter.energy_type = "纯电"
        elif "插混" in user_query or "DM-i" in user_query:
            es_filter.energy_type = "插电式混合动力"
        
        # 提取级别
        if "SUV" in user_query.upper():
            es_filter.series_level = "SUV"
        
        return HybridSearchQuery(
            es_filter=es_filter,
            vector_query=user_query,  # 直接使用原始查询
            original_query=user_query
        )


# ==========================================
# ES 检索服务
# ==========================================
class ESSearchService:
    """
    Elasticsearch 关键字检索服务
    """
    
    @staticmethod
    async def search(
        es_filter: ESFilter,
        size: int = 20,
        min_score: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        基于 ES Filter 检索
        
        Args:
            es_filter: ES 过滤条件
            size: 返回结果数量
            min_score: 最低得分阈值
        
        Returns:
            List[Dict] - ES 检索结果
        """
        try:
            from app.core.es import es_client
            from app.services.es_service import CarESService
            
            client = es_client.get_client()
            
            # 构造 ES Query
            must_clauses = []
            filter_clauses = []
            
            # 1. 状态过滤（必须在售）
            filter_clauses.append({"term": {"status": es_filter.status or 1}})
            
            # 2. 品牌过滤
            if es_filter.brand_name:
                filter_clauses.append({"term": {"brand_name": es_filter.brand_name}})
            
            # 3. 能源类型过滤
            if es_filter.energy_type:
                filter_clauses.append({"term": {"energy_type": es_filter.energy_type}})
            
            # 4. 车型级别过滤
            if es_filter.series_level:
                # 支持部分匹配（如查询"SUV"可以匹配"紧凑型SUV"和"中型SUV"）
                filter_clauses.append({"wildcard": {"series_level": f"*{es_filter.series_level}*"}})
            
            # 5. 价格范围过滤
            if es_filter.price_min is not None or es_filter.price_max is not None:
                price_range = {}
                if es_filter.price_min is not None:
                    price_range["gte"] = es_filter.price_min
                if es_filter.price_max is not None:
                    price_range["lte"] = es_filter.price_max
                filter_clauses.append({"range": {"price": price_range}})
            
            # 6. 年款过滤
            if es_filter.year:
                filter_clauses.append({"term": {"year": es_filter.year}})
            
            # 构造完整查询
            query = {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            }
            
            # 执行查询
            response = await client.search(
                index=CarESService.INDEX_NAME,
                body={
                    "query": query,
                    "size": size,
                    "min_score": min_score,
                    "_source": ["id", "name", "brand_name", "series_name", "price", 
                               "energy_type", "series_level", "tags_text"]
                }
            )
            
            # 解析结果
            hits = response["hits"]["hits"]
            results = []
            
            for hit in hits:
                doc = hit["_source"]
                doc["score"] = hit["_score"]
                doc["source"] = "es"
                results.append(doc)
            
            logger.info(f"[ES Search] 找到 {len(results)} 条结果")
            
            return results
            
        except Exception as e:
            logger.error(f"[ES Search] 查询失败: {e}")
            return []


# ==========================================
# Milvus 向量检索服务
# ==========================================
class VectorSearchService:
    """
    Milvus 向量检索服务
    """
    
    @staticmethod
    async def search(
        query_text: str,
        top_k: int = 20,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        基于语义相似度检索
        
        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            score_threshold: 相似度阈值
        
        Returns:
            List[Dict] - 向量检索结果
        """
        try:
            from pymilvus import Collection
            
            # 1. 使用 BGE-M3 生成查询向量
            logger.info("[Vector Search] 使用 bge-m3 生成查询向量")
            query_vector = embedding_model.encode(query_text).tolist()
            
            # 2. 查询 Milvus
            try:
                collection = Collection("car_vectors")
                
                # 执行向量检索
                results = collection.search(
                    data=[query_vector],
                    anns_field="embedding",
                    param={"metric_type": "IP", "params": {"nprobe": 10}},
                    limit=top_k,
                    output_fields=["id", "name", "brand_name", "series_name", 
                                 "price", "energy_type", "series_level", "tags_text"]
                )
                
                # 解析结果
                search_results = []
                if results and len(results) > 0:
                    for hit in results[0]:
                        if hit.score >= score_threshold:
                            doc = hit.entity.to_dict()
                            doc["score"] = hit.score
                            doc["source"] = "vector"
                            search_results.append(doc)
                
                logger.info(f"[Vector Search] 找到 {len(search_results)} 条结果")
                return search_results
                
            except Exception as e:
                logger.warning(f"[Vector Search] Milvus 查询失败（可能未初始化集合）: {e}")
                return []
            
        except Exception as e:
            logger.error(f"[Vector Search] 查询失败: {e}")
            return []


# ==========================================
# 混合检索服务（主服务）
# ==========================================
class HybridSearchService:
    """
    混合检索服务：ES + Milvus
    """
    
    @staticmethod
    async def search(
        user_query: str,
        top_k: int = 10,
        use_vector: bool = True,
        rerank: bool = True
    ) -> List[SearchResult]:
        """
        执行混合检索
        
        Args:
            user_query: 用户查询
            top_k: 返回结果数量
            use_vector: 是否使用向量检索
            rerank: 是否重排序
        
        Returns:
            List[SearchResult]
        """
        logger.info(f"\n[Hybrid Search] 查询: {user_query}")
        
        # 1. 解析查询
        hybrid_query = await QueryParser.parse(user_query)
        
        # 2. ES 检索
        es_results = await ESSearchService.search(
            es_filter=hybrid_query.es_filter,
            size=top_k * 2  # 多取一些，后续 Rerank
        )
        
        # 3. 向量检索（如果启用）
        vector_results = []
        if use_vector and hybrid_query.vector_query:
            vector_results = await VectorSearchService.search(
                query_text=hybrid_query.vector_query,
                top_k=top_k
            )
        
        # 4. 融合结果
        if not use_vector or not vector_results:
            # 仅使用 ES 结果
            final_results = es_results[:top_k]
        else:
            # 实现 Rerank（RRF 算法 + BGE Reranker）
            final_results = HybridSearchService._merge_results(
                es_results, 
                vector_results, 
                top_k, 
                rerank
            )
        
        # 5. 转换为 Pydantic 模型
        search_results = []
        for doc in final_results:
            try:
                result = SearchResult(
                    id=doc.get("id"),
                    name=doc.get("name", ""),
                    brand_name=doc.get("brand_name", ""),
                    series_name=doc.get("series_name", ""),
                    price=doc.get("price", 0.0),
                    energy_type=doc.get("energy_type", ""),
                    series_level=doc.get("series_level", ""),
                    score=doc.get("score", 0.0),
                    source=doc.get("source", "hybrid"),
                    tags_text=doc.get("tags_text")
                )
                search_results.append(result)
            except Exception as e:
                logger.error(f"[Hybrid Search] 结果转换失败: {e}")
                continue
        
        logger.info(f"[Hybrid Search] 返回 {len(search_results)} 条结果\n")
        
        return search_results
    
    @staticmethod
    def _merge_results(
        es_results: List[Dict],
        vector_results: List[Dict],
        top_k: int,
        rerank: bool
    ) -> List[Dict]:
        """
        融合 ES 和向量检索结果
        
        使用 RRF (Reciprocal Rank Fusion) 算法 + BGE Reranker 重排序
        """
        if not rerank:
            # 简单合并：ES 结果优先
            merged = es_results + vector_results
            seen_ids = set()
            unique_results = []
            for doc in merged:
                if doc["id"] not in seen_ids:
                    seen_ids.add(doc["id"])
                    unique_results.append(doc)
            return unique_results[:top_k]
        
        # Step 1: RRF 初步融合
        k = 60  # RRF 参数
        doc_scores = {}
        
        # ES 结果
        for rank, doc in enumerate(es_results, start=1):
            doc_id = doc["id"]
            rrf_score = 1.0 / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
        
        # 向量结果
        for rank, doc in enumerate(vector_results, start=1):
            doc_id = doc["id"]
            rrf_score = 1.0 / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
        
        # 排序
        sorted_doc_ids = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 构造候选结果（取 top_k * 2，为 Reranker 提供更多选择）
        all_docs = {doc["id"]: doc for doc in es_results + vector_results}
        candidate_results = []
        
        for doc_id, score in sorted_doc_ids[:top_k * 2]:
            if doc_id in all_docs:
                doc = all_docs[doc_id]
                doc["rrf_score"] = score
                candidate_results.append(doc)
        
        # Step 2: 使用 BGE Reranker 重排序（如果有查询文本）
        try:
            # 从候选结果中提取查询文本（假设保存在 metadata 中）
            # 这里需要传入原始查询，实际使用时需要调整
            # reranked = reranker_model.rerank(query, candidate_results, top_k)
            # 
            # 由于这里拿不到原始查询，暂时跳过 Reranker
            # 在 HybridSearchService.search 中会调用
            
            merged_results = candidate_results[:top_k]
            for doc in merged_results:
                doc["source"] = "hybrid"
            
            return merged_results
            
        except Exception as e:
            logger.warning(f"[Merge Results] Reranker 失败，使用 RRF 结果: {e}")
            
            merged_results = candidate_results[:top_k]
            for doc in merged_results:
                doc["source"] = "hybrid"
            
            return merged_results


# ==========================================
# 便捷函数
# ==========================================
async def hybrid_search(user_query: str, top_k: int = 10) -> List[SearchResult]:
    """
    便捷函数：执行混合检索
    
    使用示例:
        results = await hybrid_search("20万左右的SUV有哪些推荐")
        for result in results:
            print(f"{result.name} - {result.price}万 - 得分: {result.score}")
    """
    return await HybridSearchService.search(user_query, top_k)
