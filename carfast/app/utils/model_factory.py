# app/utils/model_factory.py
"""
多模型工厂：根据任务类型选择合适的模型
"""
import os
from enum import Enum
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import StdOutCallbackHandler
from dotenv import load_dotenv
from app.config import settings

load_dotenv(override=True)


class ModelType(str, Enum):
    """模型类型枚举"""
    BRAIN = "brain"        # 大脑：复杂推理、代码生成
    QUICK = "quick"        # 快嘴：闲聊、简单任务
    VISION = "vision"      # 眼睛：视觉识别
    EMBEDDING = "embedding"  # 图书馆管理员：向量化


class ModelFactory:
    """
    多模型工厂
    
    根据任务类型自动选择最合适的模型：
    - brain (大脑): qwen2.5-coder:14b - 复杂推理、意图识别、数据提取
    - quick (快嘴): qwen2.5:7b - 闲聊、简单问答
    - vision (眼睛): minicpm-v - 图像识别（预留）
    - embedding (图书馆管理员): bge-m3 - 文本向量化
    """
    
    # 模型配置
    MODELS = {
        ModelType.BRAIN: {
            "name": "qwen2.5-coder:14b",
            "description": "大脑 - 复杂推理和代码生成",
            "temperature": 0.3,  # 较低温度，保证稳定性
            "use_cases": ["意图识别", "数据提取", "查询解析", "复杂推理"]
        },
        ModelType.QUICK: {
            "name": "qwen2.5:7b",
            "description": "快嘴 - 闲聊和简单任务",
            "temperature": 0.8,  # 较高温度，更自然
            "use_cases": ["闲聊", "打招呼", "简单问答", "快速响应"]
        },
        ModelType.VISION: {
            "name": "minicpm-v",
            "description": "眼睛 - 视觉识别",
            "temperature": 0.5,
            "use_cases": ["图像识别", "OCR", "车辆识别"]
        }
    }
    
    @staticmethod
    def get_callbacks():
        """获取回调处理器"""
        return [StdOutCallbackHandler()]
    
    @staticmethod
    def get_llm(
        model_type: ModelType = ModelType.BRAIN,
        temperature: Optional[float] = None,
        verbose: bool = False
    ) -> ChatOllama:
        """
        根据模型类型获取 LLM
        
        Args:
            model_type: 模型类型（brain/quick/vision）
            temperature: 温度（可选，默认使用预设值）
            verbose: 是否显示详细日志
        
        Returns:
            ChatOllama 实例
        
        使用示例:
            # 复杂推理（意图识别、数据提取）
            llm = ModelFactory.get_llm(ModelType.BRAIN)
            
            # 简单闲聊
            llm = ModelFactory.get_llm(ModelType.QUICK)
        """
        # 优先使用 DeepSeek API（如果配置了）
        api_key = os.getenv("DEEPSEEK_API_KEY") or getattr(settings, "DEEPSEEK_API_KEY", "")
        
        if api_key:
            print(f"⚡ [Model] 使用 DeepSeek API (deepseek-chat)")
            return ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=api_key,
                openai_api_base="https://api.deepseek.com",
                temperature=temperature or 0.7,
                callbacks=ModelFactory.get_callbacks() if verbose else None,
                verbose=verbose
            )
        
        # 使用本地 Ollama 模型
        model_config = ModelFactory.MODELS.get(model_type)
        if not model_config:
            raise ValueError(f"未知的模型类型: {model_type}")
        
        model_name = model_config["name"]
        default_temp = model_config["temperature"]
        
        print(f"🤖 [Model] 使用本地模型: {model_name} ({model_config['description']})")
        
        return ChatOllama(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=temperature if temperature is not None else default_temp,
            callbacks=ModelFactory.get_callbacks() if verbose else None
        )
    
    @staticmethod
    def get_brain_model(temperature: float = 0.3) -> ChatOllama:
        """
        获取"大脑"模型（qwen2.5-coder:14b）
        
        适用场景：
        - 意图识别（Intent Router）
        - 查询解析（Query Parser）
        - 数据提取（Data Extraction）
        - 复杂推理
        """
        return ModelFactory.get_llm(ModelType.BRAIN, temperature)
    
    @staticmethod
    def get_quick_model(temperature: float = 0.8) -> ChatOllama:
        """
        获取"快嘴"模型（qwen2.5:7b）
        
        适用场景：
        - 闲聊（Chat Node）
        - 打招呼
        - 简单问答
        - RAG 生成（基于检索结果生成答案）
        """
        return ModelFactory.get_llm(ModelType.QUICK, temperature)


# ==========================================
# 向量化模型（BGE-M3）
# ==========================================
class EmbeddingModel:
    """
    向量化模型：bge-m3
    
    使用 sentence-transformers 加载本地模型
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """
        加载 BGE-M3 模型
        
        优先加载本地模型，如果没有则自动下载
        """
        try:
            from sentence_transformers import SentenceTransformer
            import os
            from pathlib import Path
            
            print("📚 [Embedding] 加载 bge-m3 模型...")
            
            # 检查本地模型路径（按优先级）
            model_paths = [
                Path("D:/biancheng/models/bge-m3"),  # 优先：用户指定的统一模型目录
                Path(__file__).parent.parent.parent / "models" / "bge-m3"  # 备用：项目目录
            ]
            
            local_model_path = None
            for path in model_paths:
                if path.exists():
                    local_model_path = path
                    break
            
            if local_model_path:
                # 使用本地模型
                print(f"   使用本地模型: {local_model_path}")
                self._model = SentenceTransformer(
                    str(local_model_path),
                    trust_remote_code=True
                )
            else:
                # 自动下载（使用国内镜像）
                print("   本地模型不存在，从镜像源下载...")
                os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
                
                self._model = SentenceTransformer(
                    "BAAI/bge-m3",
                    trust_remote_code=True,
                    cache_folder=None
                )
            
            print(f"✅ [Embedding] bge-m3 模型加载成功")
            
        except Exception as e:
            print(f"⚠️ [Embedding] bge-m3 模型加载失败: {e}")
            print("\n提示：")
            print("  请将模型下载到以下任一位置：")
            print("    1. D:\\biancheng\\models\\bge-m3 （推荐）")
            print("    2. <项目目录>\\models\\bge-m3")
            print("\n  下载命令：")
            print("    modelscope download --model ZhipuAI/bge-m3 --local_dir D:\\biancheng\\models\\bge-m3")
            self._model = None
    
    def encode(self, texts, batch_size: int = 32, show_progress: bool = False):
        """
        将文本转换为向量
        
        Args:
            texts: 单个文本或文本列表
            batch_size: 批处理大小
            show_progress: 是否显示进度条
        
        Returns:
            numpy.ndarray: 向量（单个文本）或向量列表（多个文本）
        """
        if self._model is None:
            raise RuntimeError("Embedding 模型未加载")
        
        return self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True  # 归一化，便于计算余弦相似度
        )
    
    @property
    def dimension(self) -> int:
        """向量维度"""
        if self._model is None:
            return 0
        return self._model.get_sentence_embedding_dimension()


# ==========================================
# 重排序模型（BGE Reranker）
# ==========================================
class RerankerModel:
    """
    重排序模型：bge-reranker-v2-m3
    
    用于对检索结果进行重排序，提升相关性
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """
        加载 BGE Reranker 模型
        
        优先加载本地模型，如果没有则自动下载
        """
        try:
            from sentence_transformers import CrossEncoder
            import os
            from pathlib import Path
            
            print("🔄 [Reranker] 加载 bge-reranker-v2-m3 模型...")
            
            # 检查本地模型路径（按优先级）
            model_paths = [
                Path("D:/biancheng/models/bge-reranker-v2-m3"),  # 优先：用户指定的统一模型目录
                Path(__file__).parent.parent.parent / "models" / "bge-reranker-v2-m3"  # 备用：项目目录
            ]
            
            local_model_path = None
            for path in model_paths:
                if path.exists():
                    local_model_path = path
                    break
            
            if local_model_path:
                # 使用本地模型
                print(f"   使用本地模型: {local_model_path}")
                self._model = CrossEncoder(
                    str(local_model_path),
                    max_length=512,
                    trust_remote_code=True
                )
            else:
                # 自动下载（使用国内镜像）
                print("   本地模型不存在，从镜像源下载...")
                os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
                
                self._model = CrossEncoder(
                    "BAAI/bge-reranker-v2-m3",
                    max_length=512,
                    trust_remote_code=True
                )
            
            print(f"✅ [Reranker] bge-reranker-v2-m3 模型加载成功")
            
        except Exception as e:
            print(f"⚠️ [Reranker] bge-reranker-v2-m3 模型加载失败: {e}")
            print("\n提示：")
            print("  请将模型下载到以下任一位置：")
            print("    1. D:\\biancheng\\models\\bge-reranker-v2-m3 （推荐）")
            print("    2. <项目目录>\\models\\bge-reranker-v2-m3")
            print("\n  下载命令：")
            print("    modelscope download --model ZhipuAI/bge-reranker-v2-m3 --local_dir D:\\biancheng\\models\\bge-reranker-v2-m3")
            self._model = None
    
    def rerank(self, query: str, documents: list, top_k: int = 10):
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表（字符串或字典，如果是字典需要有 'text' 或 'content' 字段）
            top_k: 返回前 k 个结果
        
        Returns:
            排序后的文档列表，每个文档包含 'score' 字段
        """
        if self._model is None:
            raise RuntimeError("Reranker 模型未加载")
        
        # 提取文本
        texts = []
        for doc in documents:
            if isinstance(doc, str):
                texts.append(doc)
            elif isinstance(doc, dict):
                texts.append(doc.get('text') or doc.get('content') or doc.get('name', ''))
            else:
                texts.append(str(doc))
        
        # 构造 query-document 对
        pairs = [[query, text] for text in texts]
        
        # 计算相关性得分
        scores = self._model.predict(pairs)
        
        # 排序
        sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        
        # 构造返回结果
        reranked = []
        for idx in sorted_indices[:top_k]:
            doc = documents[idx]
            if isinstance(doc, dict):
                doc['rerank_score'] = float(scores[idx])
            else:
                doc = {'text': doc, 'rerank_score': float(scores[idx])}
            reranked.append(doc)
        
        return reranked


# ==========================================
# 单例实例
# ==========================================
embedding_model = EmbeddingModel()
reranker_model = RerankerModel()
