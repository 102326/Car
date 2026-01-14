import asyncio
import random
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from faker import Faker

# =========================================================================
# 1. 导入你的模型 (请根据实际文件路径调整此处导入)
# =========================================================================
# 假设你的模型都在 app.models 模块下，或者你将之前的代码保存为了 models.py

from app.models.user import UserAuth, UserProfile, UserAddress
from app.models.car import CarBrand, CarSeries, CarModel, CarDealer
from app.models.Content_Resource import UsedCarListing, CMSPost

# =========================================================================
# 2. 配置数据库连接
# =========================================================================
DATABASE_URL = "postgresql+asyncpg://postgres:123456@47.94.10.217/car"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={
        "server_settings": {
            # 意思: "先去 car 模式找，找不到再去 public 找"
            "search_path": "car,public"
        }
    }
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
fake = Faker("zh_CN")  # 使用中文语言包

# =========================================================================
# 3. 静态字典数据 (为了让App看起来真实，核心汽车数据不使用随机生成)
# =========================================================================
REAL_CARS = {
    "比亚迪": {
        "logo": "https://img.yiche.com/byd_logo.png",
        "series": {
            "秦PLUS": ["2025款 DM-i 55KM 领先型", "2025款 EV 500KM 尊贵型"],
            "汉": ["2026款 DM-p 战神版", "2026款 EV 创世版"],
            "宋PLUS": ["2025款 DM-i 110KM 旗舰型"]
        }
    },
    "奥迪": {
        "logo": "https://img.yiche.com/audi_logo.png",
        "series": {
            "奥迪A4L": ["2026款 40 TFSI 时尚动感型", "2026款 45 TFSI 臻选动感型"],
            "奥迪Q5L": ["2025款 40 TFSI 豪华动感型"]
        }
    },
    "特斯拉": {
        "logo": "https://img.yiche.com/tesla_logo.png",
        "series": {
            "Model 3": ["2026款 后轮驱动焕新版", "2026款 长续航全轮驱动版"],
            "Model Y": ["2026款 后轮驱动版", "2026款 Performance高性能版"]
        }
    }
}


async def seed_cars(session: AsyncSession):
    print("🚗 正在生成真实汽车品牌库...")
    brands_map = {}
    series_map = {}
    models_list = []

    for brand_name, data in REAL_CARS.items():
        # 创建品牌
        brand = CarBrand(
            name=brand_name,
            logo_url=data["logo"],
            first_letter=fake.random_element(["A", "B", "T"]),  # 简化处理
            hot_rank=random.randint(1, 100)
        )
        session.add(brand)
        await session.flush()  # 获取ID
        brands_map[brand_name] = brand

        # 创建车系
        for series_name, model_names in data["series"].items():
            series = CarSeries(
                brand_id=brand.id,
                name=series_name,
                level=random.choice(["紧凑型车", "中型SUV", "中大型车"]),
                energy_type=random.choice(["插电混动", "纯电", "燃油"]),
                min_price_guidance=Decimal(random.uniform(10, 20)),
                max_price_guidance=Decimal(random.uniform(25, 40))
            )
            session.add(series)
            await session.flush()
            series_map[series_name] = series

            # 创建车型
            for model_name in model_names:
                model = CarModel(
                    series_id=series.id,
                    name=model_name,
                    year="2026",
                    price_guidance=Decimal(random.uniform(12, 35)),
                    status=1,
                    extra_tags={"subsidy": random.choice([0, 5000, 10000])}
                )
                session.add(model)
                models_list.append(model)

    print(f"✅ 完成：{len(brands_map)} 个品牌, {len(series_map)} 个车系, {len(models_list)} 款车型")
    return models_list


async def seed_users(session: AsyncSession, count=20):
    print(f"👤 正在生成 {count} 个模拟用户...")
    users = []
    for _ in range(count):
        # 创建 Auth
        user_auth = UserAuth(
            phone=fake.phone_number(),
            email=fake.email(),
            status=1
        )
        session.add(user_auth)
        await session.flush()

        # 创建 Profile
        profile = UserProfile(
            user_id=user_auth.id,
            nickname=fake.name(),
            avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_auth.id}",
            bio=fake.sentence(),
            level=random.randint(1, 10),
            is_dealer=random.choice([True, False])
        )
        session.add(profile)
        users.append(user_auth)

        # 顺便给部分用户加个地址
        if random.random() > 0.5:
            addr = UserAddress(
                user_id=user_auth.id,
                contact_name=profile.nickname,
                contact_phone=user_auth.phone,
                province=fake.province(),
                city=fake.city(),
                detail_addr=fake.street_address(),
                is_default=True
            )
            session.add(addr)

    print("✅ 用户生成完毕")
    return users


async def seed_used_cars(session: AsyncSession, users, models, count=30):
    print(f"💰 正在上架 {count} 辆二手车...")
    for _ in range(count):
        seller = random.choice(users)
        car = random.choice(models)

        listing = UsedCarListing(
            seller_id=seller.id,
            car_model_id=car.id,
            price=car.price_guidance * Decimal(0.7),  # 打7折
            mileage=Decimal(random.uniform(0.5, 8.0)),
            reg_date=fake.date_time_between(start_date="-3y", end_date="-1y"),
            city=fake.city_name(),
            description=fake.text(max_nb_chars=50),
            status=1
        )
        session.add(listing)
    print("✅ 二手车上架完毕")


async def seed_posts(session: AsyncSession, users, count=50):
    print(f"📝 正在发布 {count} 篇社区帖子...")
    for _ in range(count):
        author = random.choice(users)
        post = CMSPost(
            user_id=author.id,
            title=fake.sentence(nb_words=6),
            content_body=fake.paragraph(nb_sentences=5),
            post_type=random.choice(["article", "video"]),
            view_count=random.randint(100, 50000),
            like_count=random.randint(10, 2000),
            ip_location=fake.province()
        )
        session.add(post)
    print("✅ 帖子发布完毕")


async def main():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. 基础车型数据
            models = await seed_cars(session)

            # 2. 用户数据
            users = await seed_users(session, count=20)

            # 3. 业务数据
            await seed_used_cars(session, users, models, count=30)
            await seed_posts(session, users, count=40)

            # 4. 生成一些经销商
            print("🏢 生成经销商...")
            for _ in range(10):
                dealer = CarDealer(
                    name=fake.company() + "4S店",
                    city=fake.city_name(),
                    phone=fake.phone_number(),
                    latitude=Decimal(fake.latitude()),
                    longitude=Decimal(fake.longitude())
                )
                session.add(dealer)

        print("\n🎉🎉🎉 所有测试数据写入成功！前端现在有内容展示了！")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("已取消")
    except Exception as e:
        print(f"❌ 发生错误: {e}")