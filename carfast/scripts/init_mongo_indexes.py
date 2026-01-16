"""
初始化 MongoDB 索引
运行一次即可，为爬虫数据建立唯一索引防止重复
"""
import asyncio
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings


async def init_indexes():
    """初始化 MongoDB 索引"""
    
    print("=" * 60)
    print("  MongoDB 索引初始化")
    print("=" * 60)
    
    # 连接数据库
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client.yiche_flexible
    collection = db.car_reviews_raw
    
    try:
        # 1. 为 content_hash 创建唯一索引（防止重复数据）
        print("\n[1/3] 创建 content_hash 唯一索引...")
        await collection.create_index(
            [("content_hash", 1)],
            unique=True,
            name="idx_content_hash_unique"
        )
        print("✅ content_hash 唯一索引创建成功")
        
        # 2. 为 series_id 创建普通索引（加速查询）
        print("\n[2/3] 创建 series_id 索引...")
        await collection.create_index(
            [("series_id", 1)],
            name="idx_series_id"
        )
        print("✅ series_id 索引创建成功")
        
        # 3. 为 page 创建索引（辅助查询）
        print("\n[3/3] 创建 page 索引...")
        await collection.create_index(
            [("page", 1)],
            name="idx_page"
        )
        print("✅ page 索引创建成功")
        
        # 列出所有索引
        print("\n" + "=" * 60)
        print("  现有索引列表")
        print("=" * 60)
        indexes = await collection.list_indexes().to_list(length=None)
        for idx in indexes:
            print(f"  - {idx['name']}: {idx.get('key', {})}")
            if idx.get('unique'):
                print(f"    (唯一索引)")
        
        print("\n✅ 索引初始化完成！")
        
    except Exception as e:
        print(f"\n❌ 索引创建失败: {e}")
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(init_indexes())
