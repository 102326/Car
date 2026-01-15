# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    APP_NAME: str = "CarFast API"

    # === 钉钉配置 ===
    DINGTALK_APPID: str
    DINGTALK_APPSECRET: str

    # === JWT 配置 ===
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # === 1. 关系型数据库 (PostgreSQL) ===
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    DB_URL: str

    # === 2. [新增] 文档数据库 (MongoDB) ===
    # 用于存储聊天记录、系统日志
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "pylab_chat_db"

    # === 3. [新增] 向量数据库 (Milvus) ===
    # 用于 RAG 检索
    MILVUS_HOST: str = "127.0.0.1"
    MILVUS_PORT: str = "19530"
    # 定义两个集合：一个存课程元数据(Layer1)，一个存知识点切片(Layer2)
    MILVUS_COLLECTION_COURSE: str = "pylab_course_meta"
    MILVUS_COLLECTION_KNOWLEDGE: str = "pylab_knowledge_chunks"

    # === 4. 消息队列 (RabbitMQ) ===
    # 这里的默认值改为 user:password，这是 Docker 启动 RabbitMQ 的默认账号密码
    RABBITMQ_URL: str = "amqp://admin:123@127.0.0.1:5672/"

    # === Celery 配置 (任务队列) ===
    # [架构升级] 建议将 Broker 改为 RabbitMQ，Result Backend 保持 Redis
    # 如果你想暂时保持 Redis 做 Broker，可以不改这里，但为了可靠性建议切换
    CELERY_BROKER_URL: str = "amqp://user:password@127.0.0.1:5672/"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/2"

    # === 七牛云配置 (保持原样) ===
    QINIU_ACCESS_KEY: str
    QINIU_SECRET_KEY: str
    QINIU_BUCKET_NAME: str
    QINIU_DOMAIN: str

    # === 百度云 OCR ===
    BAIDU_APP_ID: str = ""
    BAIDU_API_KEY: str = ""
    BAIDU_SECRET_KEY: str = ""

    # === AI / LLM 配置 ===
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL_NAME: str = "deepseek-chat"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-zh-v1.5"
    ES_URL: str = "http://127.0.0.1:9200"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()