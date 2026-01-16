import asyncio
import os

import httpx
import string
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# 导入你之前定义的模型
# 确保 path 指向正确
try:
    from app.models import CarBrand, Base
except ImportError:
    # 如果还没有模型文件，请确保上文生成的 CarBrand 类在当前作用域
    pass

# ==========================================
# 1. 配置信息 (根据你的数据库修改)
# ==========================================
API_KEY = os.environ.get("JUHE_CAR_BRAND")
API_URL = 'http://apis.juhe.cn/cxdq/brand'
DATABASE_URL = "postgresql+asyncpg://postgres:gyjcxwxb@47.94.10.217/car"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"server_settings": {"search_path": "car,public"}}
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ==========================================
# 2. 抓取逻辑
# ==========================================

async def fetch_and_save_brands():
    """遍历 A-Z 抓取并存入数据库"""
    async with AsyncSessionLocal() as session:
        async with httpx.AsyncClient() as client:

            # 生成 A-Z 列表
            letters = list(string.ascii_uppercase)
            print(API_KEY)

            for letter in letters:
                print(f"🚀 正在抓取首字母: {letter} ...")

                params = {
                    'key': API_KEY,
                    'first_letter': letter,
                }

                try:
                    response = await client.get(API_URL, params=params, timeout=10.0)
                    data = response.json()

                    if data.get("error_code") == 0:
                        brands_data = data.get("result", [])

                        for item in brands_data:
                            # 1. 检查数据库中是否已存在该品牌 (根据名称或三方ID)
                            # 这里假设我们信任 API 的 ID 或根据名字判断
                            stmt = select(CarBrand).where(CarBrand.name == item['brand_name'])
                            result = await session.execute(stmt)
                            existing_brand = result.scalar_one_or_none()

                            if not existing_brand:
                                # 2. 映射字段并创建模型实例
                                new_brand = CarBrand(
                                    name=item['brand_name'],
                                    logo_url=item['brand_logo'],
                                    first_letter=item['first_letter'],
                                    hot_rank=0  # 初始热度
                                )
                                session.add(new_brand)
                                print(f"  + 新增品牌: {item['brand_name']}")
                            else:
                                # 3. 如果存在，可以选择更新 Logo
                                existing_brand.logo_url = item['brand_logo']
                                print(f"  ~ 更新品牌: {item['brand_name']}")

                        # 每一字母处理完后提交一次，防止中途报错全丢
                        await session.commit()

                    else:
                        print(f"  ❌ 接口报错: {data.get('reason')}")

                except Exception as e:
                    print(f"  ❌ 网络或系统错误: {e}")
                    await session.rollback()

                # 适当延迟，保护 API 额度或避免被封
                await asyncio.sleep(0.5)

    print("\n✅ 全量品牌同步完成！")


if __name__ == "__main__":
    asyncio.run(fetch_and_save_brands())