from sqlalchemy import String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

# ==========================================
# 6. 系统配置域 (System Domain)
# ==========================================
from carfast.app.models.user import Base, TimestampMixin


class AppVersion(Base, TimestampMixin):
    """
    表名: sys_app_version
    功能: 强制更新控制
    """
    __tablename__ = "sys_app_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(10), comment="ios/android")
    version_code: Mapped[int] = mapped_column(Integer, comment="版本号如 100")
    version_name: Mapped[str] = mapped_column(String(20), comment="版本名如 1.0.0")

    is_force: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否强制更新")
    download_url: Mapped[str] = mapped_column(String(255))
    changelog: Mapped[str] = mapped_column(Text)


class AIChatSession(Base, TimestampMixin):
    """
    表名: ai_chat_session
    功能: AI会话上下文容器 (具体Message建议存Mongo)
    """
    __tablename__ = "ai_chat_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="SessionUUID")
    user_id: Mapped[int] = mapped_column(ForeignKey("uc_user_auth.id"), index=True)
    title: Mapped[str] = mapped_column(String(50), default="新会话")