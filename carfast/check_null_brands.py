"""
快速检查数据库中品牌数据的空值情况
"""
import asyncio
import sys
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models import CarBrand

# 设置控制台输出编码为 UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')


async def check_brand_nulls():
    async with AsyncSessionLocal() as session:
        # 1. 统计总数
        total_stmt = select(func.count()).select_from(CarBrand)
        total_result = await session.execute(total_stmt)
        total_count = total_result.scalar()
        
        print(f"📊 数据库统计")
        print("=" * 50)
        print(f"总品牌数: {total_count}")
        
        # 2. 统计 name_en 为空的数量
        name_en_null_stmt = select(func.count()).select_from(CarBrand).where(
            CarBrand.name_en.is_(None)
        )
        name_en_null_result = await session.execute(name_en_null_stmt)
        name_en_null_count = name_en_null_result.scalar()
        print(f"name_en 为空: {name_en_null_count}")
        
        # 3. 统计 country 为空的数量
        country_null_stmt = select(func.count()).select_from(CarBrand).where(
            CarBrand.country.is_(None)
        )
        country_null_result = await session.execute(country_null_stmt)
        country_null_count = country_null_result.scalar()
        print(f"country 为空: {name_en_null_count}")
        
        # 4. 统计至少有一个字段为空的数量
        any_null_stmt = select(func.count()).select_from(CarBrand).where(
            (CarBrand.name_en.is_(None)) | (CarBrand.country.is_(None))
        )
        any_null_result = await session.execute(any_null_stmt)
        any_null_count = any_null_result.scalar()
        print(f"至少一个字段为空: {any_null_count}")
        
        # 5. 查看前5个需要补全的品牌
        print("\n" + "=" * 50)
        print("📋 前5个需要补全的品牌:")
        print("=" * 50)
        
        sample_stmt = select(CarBrand).where(
            (CarBrand.name_en.is_(None)) | (CarBrand.country.is_(None))
        ).limit(5)
        sample_result = await session.execute(sample_stmt)
        sample_brands = sample_result.scalars().all()
        
        if sample_brands:
            for brand in sample_brands:
                print(f"  - {brand.name}")
                print(f"    英文名: {brand.name_en or '(空)'}")
                print(f"    国家: {brand.country or '(空)'}")
                print()
        else:
            print("  ✅ 没有需要补全的数据！")


if __name__ == "__main__":
    asyncio.run(check_brand_nulls())
