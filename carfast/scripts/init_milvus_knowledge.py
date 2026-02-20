# scripts/init_milvus_knowledge.py
import os
import sys
# 将项目根目录加入路径以导入 app 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus
from app.config import settings

def build_knowledge_base():
    # 1. 模拟数据采集 (步骤 1, 2)
    raw_texts = [
        "2024年新能源汽车补贴政策：购买纯电动车最高可享受2万元补贴，插电混动车型补贴1万元。",
        "特斯拉 Model 3 焕新版采用了全新的减震器，悬架调校偏向舒适，风噪控制比老款提升了30%。",
        "比亚迪 DM-i 超级混动技术以电为主，发动机主要负责发电，亏电油耗低至 3.8L/100km。"
    ]
    docs = [Document(page_content=t, metadata={"source": "auto_news", "year": 2024}) for t in raw_texts]

    # 2. 文档拆分 (步骤 3)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )
    split_docs = text_splitter.split_documents(docs)

    # 3. 文本向量化 (步骤 4)
    # 使用你配置好的 BAAI/bge-small-zh-v1.5 模型
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)

    # 4. 存入 Milvus 向量库 (步骤 5)
    print(f"正在连接 Milvus: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    vector_db = Milvus.from_documents(
        documents=split_docs,
        embedding=embeddings,
        collection_name=settings.MILVUS_COLLECTION_KNOWLEDGE,
        connection_args={
            "host": settings.MILVUS_HOST,
            "port": settings.MILVUS_PORT
        },
        drop_old=True # 演示环境下先清空旧数据
    )
    print("知识库构建完成！共插入 {} 个 Chunk。".format(len(split_docs)))

if __name__ == "__main__":
    build_knowledge_base()