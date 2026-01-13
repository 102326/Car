from typing import Optional, List
from sqlalchemy import String, Integer, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from carfast.app.models.user import TimestampMixin, Base

# ==========================================
# 2. 车型库核心域 (Car Master Domain)
# 提示: 详细参数(spec_config)已移至MongoDB，此处仅存骨架
# ==========================================

class CarBrand(Base, TimestampMixin):
    """
    表名: car_brand
    功能: 品牌列表 (如: 奥迪, 比亚迪)
    """
    __tablename__ = "car_brand"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), index=True, comment="品牌中文名")
    name_en: Mapped[Optional[str]] = mapped_column(String(50), comment="英文名")
    logo_url: Mapped[str] = mapped_column(String(255), comment="Logo地址")

    first_letter: Mapped[str] = mapped_column(String(1), index=True, comment="首字母索引(A-Z)")
    country: Mapped[Optional[str]] = mapped_column(String(50), comment="所属国家")
    hot_rank: Mapped[int] = mapped_column(Integer, default=0, comment="热度排序权重")

    series: Mapped[List["CarSeries"]] = relationship("CarSeries", back_populates="brand")


class CarSeries(Base, TimestampMixin):
    """
    表名: car_series
    功能: 车系 (如: 奥迪A4L, 秦PLUS)
    """
    __tablename__ = "car_series"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("car_brand.id"), index=True)

    name: Mapped[str] = mapped_column(String(50), comment="车系名称")
    level: Mapped[str] = mapped_column(String(20), comment="级别(紧凑型SUV/中型车)")
    energy_type: Mapped[str] = mapped_column(String(20), comment="能源类型(燃油/插混/纯电)")

    # 价格区间用于快速筛选，无需Join查所有Model
    min_price_guidance: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), comment="最低指导价(万)")
    max_price_guidance: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), comment="最高指导价(万)")

    brand: Mapped["CarBrand"] = relationship("CarBrand", back_populates="series")
    models: Mapped[List["CarModel"]] = relationship("CarModel", back_populates="series")


class CarModel(Base, TimestampMixin):
    """
    表名: car_model
    功能: 具体车型款型 (如: 2026款 冠军版 DM-i 120km)
    注意: 复杂的 spec_config 存 Mongo，此处保留核心交易字段
    """
    __tablename__ = "car_model"

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("car_series.id"), index=True)

    name: Mapped[str] = mapped_column(String(100), comment="款型名称")
    year: Mapped[str] = mapped_column(String(4), comment="年款(2025/2026)")
    price_guidance: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), comment="官方指导价(万)")

    status: Mapped[int] = mapped_column(Integer, default=1, comment="1在售 0停售 2未上市")

    # 使用 JSONB 存储少量关键标签，避免查 Mongo
    # 例如: {"subsidy": 15000, "tags": ["包含充电桩", "免购置税"]}
    extra_tags: Mapped[Optional[dict]] = mapped_column(JSONB, comment="关键营销标签")

    series: Mapped["CarSeries"] = relationship("CarSeries", back_populates="models")


class CarDealer(Base, TimestampMixin):
    """
    表名: car_dealer
    功能: 线下经销商信息
    """
    __tablename__ = "car_dealer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), comment="经销商全称")

    # 简单的地理位置，高阶功能可用 PostGIS
    province: Mapped[str] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(50), index=True)
    latitude: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 6), comment="纬度")
    longitude: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 6), comment="经度")

    phone: Mapped[str] = mapped_column(String(20), comment="销售热线")
    main_brand_id: Mapped[int] = mapped_column(Integer, comment="主营品牌ID")