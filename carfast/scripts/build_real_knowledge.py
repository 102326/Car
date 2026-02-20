# scripts/build_real_knowledge.py
import os
import sys
import re

# 将项目根目录加入路径以导入 app 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus
from app.config import settings

# 定义原始数据目录 (步骤 1: 外部知识来源)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw_docs")


def clean_text(text: str) -> str:
    """
    步骤 2: 数据清洗与预处理
    去除多余的空行、空格、以及 PDF 解析常带的乱码字符
    """
    # 替换多个连续换行为两个换行 (保留段落结构)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 替换多个连续空格为一个空格
    text = re.sub(r'\s{2,}', ' ', text)
    # 剔除可能存在的不可见控制字符 (去噪)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return text.strip()


def load_and_process_documents():
    if not os.path.exists(DATA_DIR):
        print(f"数据目录不存在，请创建并放入文档: {DATA_DIR}")
        return []

    all_docs = []
    print(f"开始扫描目录: {DATA_DIR}")

    for filename in os.listdir(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)
        docs = []

        # 1. 根据文件后缀选择合适的 Loader
        if filename.endswith(".pdf"):
            print(f"📄 解析 PDF: {filename}")
            loader = PyPDFLoader(filepath)
            docs = loader.load()
        elif filename.endswith(".md"):
            print(f"📝 解析 Markdown: {filename}")
            # 改为使用 TextLoader，它非常轻量且不会触发 nltk 网络下载
            loader = TextLoader(filepath, encoding="utf-8")
            docs = loader.load()
        elif filename.endswith(".txt"):
            print(f"📃 解析 TXT: {filename}")
            loader = TextLoader(filepath, encoding="utf-8")
            docs = loader.load()
        else:
            print(f"⏭️ 跳过不支持的文件: {filename}")
            continue

        # 2. 执行数据清洗并注入来源元数据
        for doc in docs:
            doc.page_content = clean_text(doc.page_content)
            # 强化元数据，方便以后做限定知识库的查询 (步骤 9 中的元数据过滤)
            doc.metadata["source_file"] = filename
            doc.metadata["doc_type"] = filename.split('.')[-1]

        all_docs.extend(docs)

    return all_docs


def build_knowledge_base():
    raw_documents = load_and_process_documents()
    if not raw_documents:
        print("未找到任何有效文档内容，退出。")
        return

    # 步骤 3: 文档拆分 (Chunking)
    # 针对中文环境优化的切分器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # 每个 Chunk 大约 500 字
        chunk_overlap=50,  # 上下文重叠 50 字，防止把一句话从中间截断
        # 优先按段落切，不行再按句号切，最后才是按字切
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )

    print("✂️ 开始对文档进行语义拆分...")
    split_docs = text_splitter.split_documents(raw_documents)
    print(f"✅ 拆分完成，共生成 {len(split_docs)} 个文本块 (Chunks)。")

    # 步骤 4 & 5: 文本向量化并存入向量库
    print("🧠 正在加载 Embedding 模型...")
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)

    print(f"💾 正在写入 Milvus ({settings.MILVUS_HOST}:{settings.MILVUS_PORT})...")
    # 注意：为了测试方便，这里设置了 drop_old=True，生产环境如果增量更新需改为 False
    vector_db = Milvus.from_documents(
        documents=split_docs,
        embedding=embeddings,
        collection_name=settings.MILVUS_COLLECTION_KNOWLEDGE,
        connection_args={
            "host": settings.MILVUS_HOST,
            "port": settings.MILVUS_PORT
        },
        drop_old=True
    )
    print("🎉 真实文档知识库构建完成！")


if __name__ == "__main__":
    build_knowledge_base()