#!/usr/bin/env python3
"""
==============================================================================
 CarFast 数据种子脚本 - 批量填充 PostgreSQL 和 Elasticsearch
==============================================================================

用途:
    向数据库和搜索引擎中批量插入真实的汽车数据，使 Agent 可以搜索到实际车辆。

依赖安装:
    pip install faker sqlalchemy asyncpg elasticsearch

运行方式:
    # 在 carfast 目录下执行
    python scripts/seed_data.py
    
    # 可选参数
    python scripts/seed_data.py --clean  # 先清空旧数据再插入
    python scripts/seed_data.py --es-only  # 仅同步ES (假设PG已有数据)

Author: Antigravity
Date: 2026-01-28
"""

import sys
import asyncio
import random
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from faker import Faker
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.es import es_client
from app.models.car import CarBrand, CarSeries, CarModel, CarDealer
from app.models.user import UserAuth, UserProfile
from app.services.es_service import CarESService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

fake = Faker("zh_CN")


# ==============================================================================
# 🔧 序列重置 (解决 duplicate key 问题)
# ==============================================================================

async def reset_sequences(db: AsyncSession):
    """
    重置 PostgreSQL 序列，解决 ID 冲突问题
    在插入数据前调用，确保序列值 > 现有最大 ID
    """
    tables = ["car_brand", "car_series", "car_model"]
    
    for table in tables:
        try:
            sql = text(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'), 
                    COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, 
                    false
                )
            """)
            await db.execute(sql)
            logger.info(f"🔄 已重置序列: {table}")
        except Exception as e:
            # 如果表不存在或序列不存在，忽略错误
            logger.warning(f"⚠️ 序列重置跳过 {table}: {e}")
    
    await db.commit()

# ==============================================================================
# 📦 真实车辆数据源 (包含真实价格区间)
# ==============================================================================

CAR_DATA = {
    "奥迪": {
        "country": "德国",
        "name_en": "Audi",
        "logo_url": "https://img.autohome.com.cn/logo/brand/1.png",
        "first_letter": "A",
        "series": {
            "A4L": {
                "level": "中型车",
                "energy_type": "燃油",
                "price_range": (30, 42),
                "models": [
                    ("2024款 40 TFSI 时尚动感型", 31.28),
                    ("2024款 45 TFSI quattro 豪华型", 36.58),
                    ("2024款 45 TFSI quattro 旗舰型", 41.28),
                ]
            },
            "A6L": {
                "level": "中大型车",
                "energy_type": "燃油",
                "price_range": (42, 65),
                "models": [
                    ("2024款 45 TFSI 臻选动感型", 43.58),
                    ("2024款 55 TFSI quattro 旗舰型", 55.08),
                    ("2024款 55 TFSI quattro 尊享型", 64.88),
                ]
            },
            "Q5L": {
                "level": "中型SUV",
                "energy_type": "燃油",
                "price_range": (40, 52),
                "models": [
                    ("2024款 40 TFSI 荣享进取型", 40.08),
                    ("2024款 45 TFSI quattro 豪华动感型", 46.58),
                    ("2024款 45 TFSI quattro 尊享型", 51.92),
                ]
            },
        }
    },
    "宝马": {
        "country": "德国",
        "name_en": "BMW",
        "logo_url": "https://img.autohome.com.cn/logo/brand/2.png",
        "first_letter": "B",
        "series": {
            "3系": {
                "level": "中型车",
                "energy_type": "燃油",
                "price_range": (29, 40),
                "models": [
                    ("2024款 325i M运动曜夜套装", 30.89),
                    ("2024款 330i M运动曜夜套装", 35.89),
                    ("2024款 325Li xDrive M运动曜夜套装", 39.89),
                ]
            },
            "5系": {
                "level": "中大型车",
                "energy_type": "燃油",
                "price_range": (44, 60),
                "models": [
                    ("2024款 525Li 豪华套装", 44.99),
                    ("2024款 530Li xDrive 豪华套装", 50.99),
                    ("2024款 540Li xDrive 尊享型", 59.99),
                ]
            },
            "X3": {
                "level": "中型SUV",
                "energy_type": "燃油",
                "price_range": (40, 50),
                "models": [
                    ("2024款 xDrive25i 领先型", 40.50),
                    ("2024款 xDrive30i 领先型 M曜夜", 46.58),
                    ("2024款 xDrive30i 尊享型 M曜夜", 49.98),
                ]
            },
        }
    },
    "奔驰": {
        "country": "德国",
        "name_en": "Mercedes-Benz",
        "logo_url": "https://img.autohome.com.cn/logo/brand/3.png",
        "first_letter": "B",
        "series": {
            "C级": {
                "level": "中型车",
                "energy_type": "燃油",
                "price_range": (33, 45),
                "models": [
                    ("2024款 C 200 L 运动版", 33.98),
                    ("2024款 C 260 L 运动版", 38.92),
                    ("2024款 C 300 L 4MATIC 运动版", 44.92),
                ]
            },
            "E级": {
                "level": "中大型车",
                "energy_type": "燃油",
                "price_range": (45, 60),
                "models": [
                    ("2024款 E 260 L 运动型", 45.72),
                    ("2024款 E 300 L 运动型", 52.42),
                    ("2024款 E 300 L 4MATIC 豪华型", 59.88),
                ]
            },
            "GLC": {
                "level": "中型SUV",
                "energy_type": "燃油",
                "price_range": (42, 55),
                "models": [
                    ("2024款 GLC 260 L 4MATIC 动感型", 42.78),
                    ("2024款 GLC 300 L 4MATIC 动感型", 48.52),
                    ("2024款 GLC 300 L 4MATIC AMG-Line", 54.12),
                ]
            },
        }
    },
    "特斯拉": {
        "country": "美国",
        "name_en": "Tesla",
        "logo_url": "https://img.autohome.com.cn/logo/brand/tesla.png",
        "first_letter": "T",
        "series": {
            "Model 3": {
                "level": "中型车",
                "energy_type": "纯电",
                "price_range": (24, 34),
                "models": [
                    ("2024款 后驱 焕新版", 24.59),
                    ("2024款 长续航 全轮驱动焕新版", 29.59),
                    ("2024款 Performance 高性能焕新版", 33.59),
                ]
            },
            "Model Y": {
                "level": "中型SUV",
                "energy_type": "纯电",
                "price_range": (26, 38),
                "models": [
                    ("2024款 后驱版", 26.39),
                    ("2024款 长续航全轮驱动版", 30.99),
                    ("2024款 Performance 高性能版", 37.99),
                ]
            },
        }
    },
    "比亚迪": {
        "country": "中国",
        "name_en": "BYD",
        "logo_url": "https://img.autohome.com.cn/logo/brand/byd.png",
        "first_letter": "B",
        "series": {
            "秦PLUS": {
                "level": "紧凑型车",
                "energy_type": "插混",
                "price_range": (10, 15),
                "models": [
                    ("2024款 DM-i 冠军版 55km 领先型", 9.98),
                    ("2024款 DM-i 冠军版 120km 旗舰型", 13.98),
                ]
            },
            "汉": {
                "level": "中大型车",
                "energy_type": "插混",
                "price_range": (20, 35),
                "models": [
                    ("2024款 DM-i 冠军版 121km 尊贵型", 21.98),
                    ("2024款 DM-p 战神版 202km 四驱尊享型", 28.98),
                    ("2024款 EV 冠军版 715km 旗舰型", 32.98),
                ]
            },
            "唐": {
                "level": "中型SUV",
                "energy_type": "插混",
                "price_range": (21, 33),
                "models": [
                    ("2024款 DM-i 冠军版 112km 尊享型", 21.48),
                    ("2024款 DM-p 战神版 215km 四驱旗舰型", 28.98),
                ]
            },
        }
    },
    "理想": {
        "country": "中国",
        "name_en": "Li Auto",
        "logo_url": "https://img.autohome.com.cn/logo/brand/lixiang.png",
        "first_letter": "L",
        "series": {
            "L7": {
                "level": "中大型SUV",
                "energy_type": "增程",
                "price_range": (33, 42),
                "models": [
                    ("2024款 Pro", 33.98),
                    ("2024款 Max", 37.98),
                    ("2024款 Ultra", 41.98),
                ]
            },
            "L8": {
                "level": "中大型SUV",
                "energy_type": "增程",
                "price_range": (35, 44),
                "models": [
                    ("2024款 Pro", 35.98),
                    ("2024款 Max", 39.98),
                ]
            },
            "L9": {
                "level": "大型SUV",
                "energy_type": "增程",
                "price_range": (43, 48),
                "models": [
                    ("2024款 Pro", 43.98),
                    ("2024款 Max", 47.98),
                ]
            },
        }
    },
}

# 营销标签池 (Agent 可以匹配这些标签)
TAG_POOL = ["省油", "推背感", "家用", "商务", "保值", "准新车", 
            "高颜值", "空间大", "智能驾驶", "舒适静谧", "操控好", "动力强"]


# ==============================================================================
# 🔧 数据库操作
# ==============================================================================

async def ensure_brand(db: AsyncSession, brand_name: str, brand_data: dict) -> CarBrand:
    """确保品牌存在"""
    result = await db.execute(select(CarBrand).where(CarBrand.name == brand_name))
    brand = result.scalar_one_or_none()
    
    if not brand:
        brand = CarBrand(
            name=brand_name,
            name_en=brand_data.get("name_en"),
            logo_url=brand_data.get("logo_url", ""),
            first_letter=brand_data.get("first_letter", brand_name[0].upper()),
            country=brand_data.get("country"),
            hot_rank=random.randint(50, 100)
        )
        db.add(brand)
        await db.flush()
        logger.info(f"✅ 创建品牌: {brand_name} (ID: {brand.id})")
    else:
        logger.info(f"⏭️ 品牌已存在: {brand_name} (ID: {brand.id})")
    
    return brand


async def ensure_series(db: AsyncSession, brand: CarBrand, series_name: str, series_data: dict) -> CarSeries:
    """确保车系存在"""
    result = await db.execute(
        select(CarSeries).where(CarSeries.brand_id == brand.id, CarSeries.name == series_name)
    )
    series = result.scalar_one_or_none()
    
    if not series:
        min_price, max_price = series_data["price_range"]
        series = CarSeries(
            brand_id=brand.id,
            name=series_name,
            level=series_data["level"],
            energy_type=series_data["energy_type"],
            min_price_guidance=Decimal(str(min_price)),
            max_price_guidance=Decimal(str(max_price))
        )
        db.add(series)
        await db.flush()
        logger.info(f"  ✅ 创建车系: {series_name} (ID: {series.id})")
    else:
        logger.info(f"  ⏭️ 车系已存在: {series_name} (ID: {series.id})")
    
    return series


async def create_models(db: AsyncSession, brand: CarBrand, series: CarSeries, models_data: list) -> List[dict]:
    """创建车型，返回 ES 文档"""
    es_docs = []
    
    for model_name, price in models_data:
        result = await db.execute(
            select(CarModel).where(CarModel.series_id == series.id, CarModel.name == model_name)
        )
        existing = result.scalar_one_or_none()
        
        tags = random.sample(TAG_POOL, k=random.randint(2, 4))
        
        if existing:
            car_id = existing.id
            tags = existing.extra_tags.get("tags", tags) if existing.extra_tags else tags
        else:
            model = CarModel(
                series_id=series.id,
                name=model_name,
                year=model_name[:4],
                price_guidance=Decimal(str(price)),
                status=1,
                extra_tags={"tags": tags}
            )
            db.add(model)
            await db.flush()
            car_id = model.id
            logger.info(f"    ✅ 创建款型: {model_name} (ID: {car_id})")
        
        # ES 文档
        es_docs.append({
            "id": car_id,
            "name": f"{brand.name} {series.name} {model_name}",
            "brand_name": brand.name,
            "series_name": series.name,
            "series_level": series.level,
            "energy_type": series.energy_type,
            "price": float(price),
            "year": model_name[:4],
            "status": 1,
            "tags_text": " ".join(tags),
            "updated_at": datetime.utcnow().isoformat()
        })
    
    return es_docs


async def clean_existing_data(db: AsyncSession):
    """清空旧数据"""
    logger.warning("🗑️ 清空现有车型数据...")
    await db.execute(delete(CarModel))
    await db.execute(delete(CarSeries))
    await db.execute(delete(CarBrand))
    await db.commit()
    logger.info("✅ PostgreSQL 数据已清空")
    
    client = es_client.get_client()
    try:
        await client.indices.delete(index=CarESService.INDEX_NAME, ignore_unavailable=True)
        logger.info(f"✅ Elasticsearch 索引 {CarESService.INDEX_NAME} 已删除")
    except Exception as e:
        logger.warning(f"⚠️ ES 索引删除失败: {e}")


# ==============================================================================
# 🚀 主流程
# ==============================================================================

async def seed_data(clean: bool = False, es_only: bool = False):
    """主数据填充流程"""
    logger.info("=" * 60)
    logger.info("🌱 CarFast 数据种子脚本启动")
    logger.info("=" * 60)
    
    all_es_docs = []
    
    try:
        async with AsyncSessionLocal() as db:
            # 1. 关键：先重置序列，防止 ID 冲突
            await reset_sequences(db)

            if clean:
                await clean_existing_data(db)
                # clean 后再次重置序列以防万一
                await reset_sequences(db)
            
            await CarESService.create_index_if_not_exists()
            
            for brand_name, brand_data in CAR_DATA.items():
                brand = await ensure_brand(db, brand_name, brand_data)
                
                for series_name, series_data in brand_data["series"].items():
                    series = await ensure_series(db, brand, series_name, series_data)
                    es_docs = await create_models(db, brand, series, series_data["models"])
                    all_es_docs.extend(es_docs)
            
            if not es_only:
                await db.commit()
                logger.info("✅ PostgreSQL 数据提交完成")
        
        if all_es_docs:
            logger.info(f"📤 同步 {len(all_es_docs)} 条文档到 Elasticsearch...")
            failed = await CarESService.bulk_sync_cars(all_es_docs)
            if failed:
                logger.error(f"❌ ES 同步失败 {len(failed)} 条: {failed}")
            else:
                logger.info("✅ Elasticsearch 同步完成")
                
    finally:
        # 2. 确保资源释放
        await es_client.close()
    
    logger.info("=" * 60)
    logger.info(f"🎉 完成! 品牌: {len(CAR_DATA)}, 车型: {len(all_es_docs)}")
    logger.info("=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CarFast 数据种子脚本")
    parser.add_argument("--clean", action="store_true", help="先清空旧数据再插入")
    parser.add_argument("--es-only", action="store_true", help="仅同步ES")
    args = parser.parse_args()
    
    asyncio.run(seed_data(clean=args.clean, es_only=args.es_only))


if __name__ == "__main__":
    main()