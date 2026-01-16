"""
显示当前配置（调试用）
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings


def mask_password(url: str) -> str:
    """隐藏密码"""
    if '@' in url and '//' in url:
        parts = url.split('@')
        credentials = parts[0].split('//')[1]
        if ':' in credentials:
            username = credentials.split(':')[0]
            return url.replace(credentials, f"{username}:***")
    return url


if __name__ == "__main__":
    print("=" * 60)
    print("  当前配置信息")
    print("=" * 60)
    
    print("\n[MongoDB 配置]")
    print(f"  MONGO_URL: {mask_password(settings.MONGO_URL)}")
    print(f"  MONGO_DB_NAME: {settings.MONGO_DB_NAME}")
    
    print("\n[PostgreSQL 配置]")
    print(f"  DB_URL: {mask_password(settings.DB_URL)}")
    
    print("\n[Redis 配置]")
    print(f"  REDIS_URL: {mask_password(settings.REDIS_URL)}")
    
    print("\n[RabbitMQ 配置]")
    print(f"  RABBITMQ_URL: {mask_password(settings.RABBITMQ_URL)}")
    
    print("\n[应用配置]")
    print(f"  APP_NAME: {settings.APP_NAME}")
    print(f"  SECRET_KEY: {settings.SECRET_KEY[:10]}... (已隐藏)")
    
    print("\n" + "=" * 60)
    print("  配置来源")
    print("=" * 60)
    print("  1. 系统环境变量")
    print("  2. .env 文件（当前优先）")
    print("  3. config.py 默认值")
    print("=" * 60)
