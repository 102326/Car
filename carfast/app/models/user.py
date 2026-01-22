from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs

# ==========================================
# 0. 基础模型配置 (Base Model)
# ==========================================

class Base(AsyncAttrs, DeclarativeBase):
    """所有模型的基类"""
    pass


class TimestampMixin:
    """通用时间戳混入类"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )


# ==========================================
# 1. 用户中心域 (User Domain)
# ==========================================

class UserAuth(Base, TimestampMixin):
    """
    表名: uc_user_auth
    功能: 用户核心授权表，仅存储登录凭证
    """
    __tablename__ = "uc_user_auth"

    id: Mapped[int] = mapped_column(primary_key=True, comment="用户全局唯一ID")
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, comment="手机号")
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, comment="邮箱")

    # 第三方登录标识
    wx_openid: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, comment="微信OpenID")
    apple_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, comment="AppleID")

    password_hash: Mapped[Optional[str]] = mapped_column(String(128), comment="加盐密码hash")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 1正常 0禁用 2注销")

    # 关联
    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="user", uselist=False)
    realname: Mapped["RealnameVerify"] = relationship("RealnameVerify", back_populates="user", uselist=False)


class UserProfile(Base, TimestampMixin):
    """
    表名: uc_user_profile
    功能: 用户公开档案，App展示层高频读取
    """
    __tablename__ = "uc_user_profile"

    user_id: Mapped[int] = mapped_column(ForeignKey("uc_user_auth.id"), primary_key=True, comment="关联用户ID")
    nickname: Mapped[str] = mapped_column(String(50), default="易车用户", comment="昵称")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), comment="头像地址(MinIO)")
    bio: Mapped[Optional[str]] = mapped_column(String(200), comment="个人简介")

    # 社区属性
    level: Mapped[int] = mapped_column(Integer, default=1, comment="用户等级")
    points: Mapped[int] = mapped_column(Integer, default=0, comment="积分余额")
    is_dealer: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否认证经销商")

    user: Mapped["UserAuth"] = relationship("UserAuth", back_populates="profile")


class RealnameVerify(Base, TimestampMixin):
    """
    表名: uc_realname_verify
    功能: 实名认证信息 (敏感数据加密存储)
    """
    __tablename__ = "uc_realname_verify"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("uc_user_auth.id"), unique=True, comment="用户ID")

    real_name: Mapped[str] = mapped_column(String(50), comment="真实姓名")
    id_card_enc: Mapped[str] = mapped_column(String(255), comment="身份证号(AES加密)")

    verify_status: Mapped[int] = mapped_column(Integer, default=0, comment="0待审 1通过 2驳回")
    audit_remark: Mapped[Optional[str]] = mapped_column(String(255), comment="审核备注")

    user: Mapped["UserAuth"] = relationship("UserAuth", back_populates="realname")


class UserAddress(Base, TimestampMixin):
    """
    表名: uc_address_book
    功能: 收货与定位地址
    """
    __tablename__ = "uc_address_book"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("uc_user_auth.id"), index=True)

    contact_name: Mapped[str] = mapped_column(String(50), comment="联系人")
    contact_phone: Mapped[str] = mapped_column(String(20), comment="联系电话")
    province: Mapped[str] = mapped_column(String(50), comment="省")
    city: Mapped[str] = mapped_column(String(50), comment="市")
    district: Mapped[str] = mapped_column(String(50), comment="区")
    detail_addr: Mapped[str] = mapped_column(String(255), comment="详细地址")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="默认地址")