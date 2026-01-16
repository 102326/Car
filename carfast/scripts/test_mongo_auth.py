"""
测试 MongoDB 连接和认证状态
"""
import asyncio
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings


async def test_mongo_connection():
    """测试 MongoDB 连接"""
    
    print("=" * 60)
    print("  MongoDB 连接测试")
    print("=" * 60)
    print(f"连接地址: {settings.MONGO_URL}")
    print(f"数据库名: {settings.MONGO_DB_NAME}")
    print("-" * 60)
    
    try:
        # 尝试连接
        client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
        
        # 测试连接
        print("\n[1/4] 测试连接...")
        await client.admin.command('ping')
        print("[OK] 连接成功")
        
        # 获取服务器信息
        print("\n[2/4] 获取服务器信息...")
        server_info = await client.server_info()
        print(f"[OK] MongoDB 版本: {server_info.get('version', 'Unknown')}")
        
        # 检查认证状态
        print("\n[3/4] 检查认证状态...")
        try:
            # 尝试执行需要权限的操作
            db = client[settings.MONGO_DB_NAME]
            
            # 列出集合
            collections = await db.list_collection_names()
            print(f"[OK] 可访问数据库")
            print(f"现有集合数量: {len(collections)}")
            if collections:
                print(f"集合列表: {', '.join(collections[:5])}")
                if len(collections) > 5:
                    print(f"          ... 还有 {len(collections) - 5} 个集合")
            
            # 尝试写入测试
            print("\n[4/4] 测试写入权限...")
            test_collection = db.connection_test
            result = await test_collection.insert_one({"test": "connection_test"})
            print(f"[OK] 写入成功 (ID: {result.inserted_id})")
            
            # 清理测试数据
            await test_collection.delete_one({"_id": result.inserted_id})
            print(f"[OK] 删除测试数据成功")
            
        except Exception as e:
            print(f"[ERROR] 权限测试失败: {e}")
            print("\n可能原因:")
            print("  - MongoDB 开启了认证但未提供正确的用户名密码")
            print("  - 用户权限不足")
            return False
        
        print("\n" + "=" * 60)
        print("  连接状态总结")
        print("=" * 60)
        print("[OK] MongoDB 连接正常")
        print("[OK] 当前配置无需认证（或认证已通过）")
        print("[OK] 读写权限正常")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 连接失败: {e}")
        print("\n可能原因:")
        print("  1. MongoDB 服务未启动")
        print("  2. 连接地址或端口错误")
        print("  3. 网络不通")
        print("  4. 需要认证但未提供用户名密码")
        
        print("\n解决方案:")
        print("  - 检查 MongoDB 是否运行: mongo --eval 'db.version()'")
        print("  - 检查配置: .env 中的 MONGO_URL")
        print("  - 如需认证，修改为: mongodb://user:pass@host:port")
        
        return False
        
    finally:
        client.close()


async def show_auth_examples():
    """显示认证配置示例"""
    
    print("\n\n" + "=" * 60)
    print("  MongoDB 认证配置示例")
    print("=" * 60)
    
    print("\n[1] 无认证（开发环境，当前使用）")
    print("   MONGO_URL=mongodb://47.94.10.217:27017")
    
    print("\n[2] 用户名密码认证（推荐）")
    print("   MONGO_URL=mongodb://admin:password123@47.94.10.217:27017")
    
    print("\n[3] 指定认证数据库")
    print("   MONGO_URL=mongodb://admin:password123@47.94.10.217:27017/?authSource=admin")
    
    print("\n[4] MongoDB Atlas（云服务）")
    print("   MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/dbname")
    
    print("\n[5] 本地 Docker 容器")
    print("   MONGO_URL=mongodb://root:example@localhost:27017")
    
    print("\n[6] 连接字符串完整参数")
    print("   MONGO_URL=mongodb://user:pass@host:port/database?authSource=admin&readPreference=primary")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_mongo_connection())
    asyncio.run(show_auth_examples())
