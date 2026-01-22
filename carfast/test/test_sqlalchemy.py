"""
SQLAlchemy 迁移测试脚本
用于验证数据库连接和基本 CRUD 操作
"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import UserAuth
from app.models.car import CarBrand


async def test_connection():
    """测试数据库连接"""
    print("🔌 测试数据库连接...")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserAuth).limit(1))
            user = result.scalar_one_or_none()
            if user:
                print(f"✅ 数据库连接成功！找到用户: ID={user.id}")
            else:
                print("✅ 数据库连接成功！（暂无用户数据）")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    return True


async def test_query():
    """测试查询操作"""
    print("\n🔍 测试查询操作...")
    try:
        async with AsyncSessionLocal() as session:
            # 查询用户
            result = await session.execute(select(UserAuth).limit(5))
            users = result.scalars().all()
            print(f"   用户数量: {len(users)}")
            
            # 查询品牌
            result = await session.execute(select(CarBrand).limit(5))
            brands = result.scalars().all()
            print(f"   品牌数量: {len(brands)}")
            
            print("✅ 查询操作正常")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return False
    return True


async def test_insert():
    """测试插入操作"""
    print("\n➕ 测试插入操作...")
    try:
        async with AsyncSessionLocal() as session:
            # 创建测试用户
            test_user = UserAuth(
                phone="19900000000",
                email="test_sqlalchemy@example.com",
                status=1
            )
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            
            print(f"✅ 插入成功！用户ID: {test_user.id}")
            
            # 清理测试数据
            await session.delete(test_user)
            await session.commit()
            print("✅ 测试数据已清理")
            
    except Exception as e:
        print(f"❌ 插入失败: {e}")
        return False
    return True


async def test_update():
    """测试更新操作"""
    print("\n📝 测试更新操作...")
    try:
        async with AsyncSessionLocal() as session:
            # 查找第一个用户
            result = await session.execute(select(UserAuth).limit(1))
            user = result.scalar_one_or_none()
            
            if not user:
                print("⚠️  暂无用户数据，跳过更新测试")
                return True
            
            # 记录原值
            original_status = user.status
            
            # 更新
            user.status = 1 if user.status == 0 else user.status
            await session.commit()
            print(f"✅ 更新成功！用户ID: {user.id}")
            
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return False
    return True


async def test_join():
    """测试关联查询"""
    print("\n🔗 测试关联查询...")
    try:
        from sqlalchemy.orm import selectinload
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserAuth)
                .options(selectinload(UserAuth.profile))
                .limit(1)
            )
            user = result.scalar_one_or_none()
            
            if user and user.profile:
                print(f"✅ 关联查询成功！用户: {user.profile.nickname}")
            elif user:
                print("✅ 关联查询成功！（用户无Profile）")
            else:
                print("✅ 关联查询成功！（暂无用户数据）")
                
    except Exception as e:
        print(f"❌ 关联查询失败: {e}")
        return False
    return True


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("  SQLAlchemy 2.0 迁移测试套件")
    print("=" * 60)
    
    tests = [
        ("数据库连接", test_connection),
        ("查询操作", test_query),
        ("插入操作", test_insert),
        ("更新操作", test_update),
        ("关联查询", test_join),
    ]
    
    results = []
    for name, test_func in tests:
        success = await test_func()
        results.append((name, success))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name:20s} {status}")
    
    print("-" * 60)
    print(f"  总计: {passed}/{total} 通过")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 所有测试通过！SQLAlchemy 迁移成功！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查配置")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试已取消")
    except Exception as e:
        print(f"\n\n❌ 测试运行失败: {e}")
