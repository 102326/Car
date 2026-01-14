from enum import Enum
from app.models.user import TimestampMixin, Base
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, DECIMAL, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

# ==========================================
# 3. 内容与资源域 (Content & Resource Domain)
# 提示: 复杂的文章Body或长评论链可移至MongoDB
# ==========================================

class PostType(str, Enum):
    ARTICLE = "article"
    VIDEO = "video"


class CMSPost(Base, TimestampMixin):
    """
    表名: cms_post
    功能: 社区文章/视频元数据
    """
    __tablename__ = "cms_post"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("uc_user_auth.id"), index=True)

    title: Mapped[str] = mapped_column(String(100), comment="标题")
    post_type: Mapped[PostType] = mapped_column(String(20), default=PostType.ARTICLE, comment="类型: article/video")
    cover_url: Mapped[Optional[str]] = mapped_column(String(255), comment="封面图")

    # 混合架构关键点:
    # 如果内容极长(>10KB)，建议存Mongo，此处仅存MongoID。
    # 若内容较短，直接用Text存PG即可。
    content_body: Mapped[Optional[str]] = mapped_column(Text, comment="文章内容/视频描述")
    video_url: Mapped[Optional[str]] = mapped_column(String(255), comment="视频MinIO地址")

    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1发布 0草稿 2下架")

    # 地理位置标记
    ip_location: Mapped[Optional[str]] = mapped_column(String(50), comment="发布IP属地")


class CMSComment(Base, TimestampMixin):
    """
    表名: cms_comment
    功能: 评论表 (支持两级回复)
    """
    __tablename__ = "cms_comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("cms_post.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("uc_user_auth.id"))

    content: Mapped[str] = mapped_column(String(500), comment="评论内容")
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, comment="父评论ID(楼中楼)")

    like_count: Mapped[int] = mapped_column(Integer, default=0)


class SysFileResource(Base, TimestampMixin):
    """
    表名: sys_file_resource
    功能: MinIO文件映射表 (大文件上传断点续传的基础)
    """
    __tablename__ = "sys_file_resource"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="UUID/FileID")
    file_name: Mapped[str] = mapped_column(String(255))
    file_key: Mapped[str] = mapped_column(String(255), comment="MinIO Object Key")
    file_size: Mapped[int] = mapped_column(Integer, comment="字节大小")
    mime_type: Mapped[str] = mapped_column(String(50))

    is_merged: Mapped[bool] = mapped_column(Boolean, default=False, comment="分片合并完成标记")
    md5_hash: Mapped[Optional[str]] = mapped_column(String(32), comment="文件校验")


# ==========================================
# 4. 市场域: 二手车 & 新能源 (Market Domain)
# ==========================================

class UsedCarListing(Base, TimestampMixin):
    """
    表名: used_car_listing
    功能: 二手车车源
    """
    __tablename__ = "used_car_listing"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("uc_user_auth.id"), index=True, comment="卖家ID")

    # 关联标准车型库
    car_model_id: Mapped[int] = mapped_column(ForeignKey("car_model.id"), index=True)

    price: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), comment="售价(万)")
    mileage: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), comment="里程(万公里)")
    reg_date: Mapped[datetime] = mapped_column(DateTime, comment="上牌日期")
    city: Mapped[str] = mapped_column(String(50), index=True, comment="车辆所在地")

    description: Mapped[str] = mapped_column(Text, comment="车况描述")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1上架 2已售 3审核中")


class NESubsidyPolicy(Base, TimestampMixin):
    """
    表名: ne_subsidy_policy
    功能: 新能源补贴策略 (用于计算到手价)
    """
    __tablename__ = "ne_subsidy_policy"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), comment="政策名称")
    city: Mapped[str] = mapped_column(String(50), index=True, comment="适用城市")
    amount: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), comment="补贴金额(元)")
    expire_date: Mapped[datetime] = mapped_column(DateTime, comment="过期时间")
