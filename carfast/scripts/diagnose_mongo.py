"""
MongoDB 连接诊断工具
帮助排查认证和连接问题
"""
import asyncio
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings


async def diagnose():
    """完整诊断 MongoDB 连接"""
    
    print("=" * 70)
    print("  MongoDB 连接诊断工具")
    print("=" * 70)
    
    # 显示配置
    print("\n[步骤 1] 当前配置:")
    print("-" * 70)
    
    # 隐藏密码显示
    url_display = settings.MONGO_URL
    if '@' in url_display and '//' in url_display:
        parts = url_display.split('@')
        credentials = parts[0].split('//')[1]
        if ':' in credentials:
            username = credentials.split(':')[0]
            url_display = url_display.replace(credentials, f"{username}:***")
    
    print(f"  MONGO_URL: {url_display}")
    print(f"  MONGO_DB_NAME: {settings.MONGO_DB_NAME}")
    
    # 检查配置
    print("\n[步骤 2] 配置检查:")
    print("-" * 70)
    
    checks = []
    
    if '@' in settings.MONGO_URL:
        print("  ✅ URL 包含认证信息")
        checks.append(True)
    else:
        print("  ❌ URL 缺少认证信息（没有 username:password@）")
        checks.append(False)
    
    if 'authSource' in settings.MONGO_URL:
        print("  ✅ URL 包含 authSource 参数")
        checks.append(True)
    else:
        print("  ⚠️ URL 缺少 authSource 参数（建议添加 ?authSource=admin）")
        print("     修改为: mongodb://user:pass@host:port/?authSource=admin")
        checks.append(False)
    
    # 尝试连接
    print("\n[步骤 3] 连接测试:")
    print("-" * 70)
    
    try:
        print("  正在创建客户端...")
        client = AsyncIOMotorClient(
            settings.MONGO_URL,
            serverSelectionTimeoutMS=5000
        )
        
        print("  正在测试连接（ping）...")
        await client.admin.command('ping')
        print("  ✅ 连接成功（ping 通过）")
        
        print(f"\n  正在访问数据库 '{settings.MONGO_DB_NAME}'...")
        db = client[settings.MONGO_DB_NAME]
        
        # 尝试列出集合
        print("  正在列出集合...")
        collections = await db.list_collection_names()
        print(f"  ✅ 认证成功！可以访问数据库")
        print(f"  现有集合数量: {len(collections)}")
        
        if collections:
            print(f"  集合列表:")
            for coll in collections[:10]:
                count = await db[coll].estimated_document_count()
                print(f"    - {coll}: {count} 条文档")
            if len(collections) > 10:
                print(f"    ... 还有 {len(collections) - 10} 个集合")
        else:
            print(f"  ⚠️ 数据库为空，将在首次插入时自动创建集合")
        
        # 测试写入
        print(f"\n  测试写入权限...")
        test_result = await db.connection_test.insert_one({
            "test": "connection_test",
            "timestamp": "test"
        })
        print(f"  ✅ 写入成功 (ID: {test_result.inserted_id})")
        
        # 清理测试数据
        await db.connection_test.delete_one({"_id": test_result.inserted_id})
        print(f"  ✅ 删除测试数据成功")
        
        print("\n" + "=" * 70)
        print("  ✅✅✅ 所有测试通过！MongoDB 配置正确！ ✅✅✅")
        print("=" * 70)
        print("\n  可以运行爬虫了：")
        print("    python scripts/scheduler_crawler.py")
        print()
        
        client.close()
        return True
        
    except Exception as e:
        print(f"\n  ❌ 连接失败: {e}")
        
        print("\n" + "=" * 70)
        print("  诊断结果和建议")
        print("=" * 70)
        
        error_str = str(e).lower()
        
        if 'authentication' in error_str or 'unauthorized' in error_str:
            print("\n  问题类型: 认证失败")
            print("\n  解决方案:")
            print("    1. 检查 .env 文件中的用户名和密码是否正确")
            print("    2. 添加 authSource 参数:")
            print(f"       MONGO_URL=mongodb://user:pass@host:port/?authSource=admin")
            print("\n  示例配置:")
            print("    MONGO_URL=mongodb://root:123456@47.94.10.217:27017/?authSource=admin")
            
        elif 'timeout' in error_str or 'connection' in error_str:
            print("\n  问题类型: 连接超时/失败")
            print("\n  解决方案:")
            print("    1. 检查 MongoDB 服务是否启动")
            print("    2. 检查防火墙是否开放 27017 端口")
            print("    3. 验证 IP 地址和端口是否正确")
            
        else:
            print(f"\n  问题类型: 未知错误")
            print(f"  错误详情: {e}")
        
        print("\n" + "=" * 70)
        
        client.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(diagnose())
    sys.exit(0 if success else 1)
