"""
Agent Memory Profile Model.

This module defines the persistent memory storage for the CarFast Agent,
enabling personalized recommendations based on user preferences.

Part of Phase E: Agent Memory System.
"""

from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base, TimestampMixin


class AgentMemoryProfile(Base, TimestampMixin):
    """
    表名: ai_agent_memory
    功能: Agent 记忆存储 - 用户购车偏好画像
    
    设计原则:
    1. 与 UserProfile (展示型) 分离，专注于 AI 决策
    2. extra_data JSON 字段提供扩展性，避免频繁 Schema 变更
    3. version 字段用于乐观锁并发控制
    """
    __tablename__ = "ai_agent_memory"

    # 主键 - 与用户一对一
    user_id: Mapped[int] = mapped_column(
        ForeignKey("uc_user_auth.id"),
        primary_key=True,
        comment="关联用户ID"
    )

    # ==========================================
    # 核心偏好字段 (Hot Fields)
    # ==========================================
    
    preference_brand: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="偏好品牌 (逗号分隔, 如 '宝马,奔驰')"
    )
    
    budget_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="预算下限 (万元)"
    )
    
    budget_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="预算上限 (万元)"
    )
    
    preference_tags: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="偏好标签 (如 ['SUV', '省油', '家用'])"
    )

    # ==========================================
    # 扩展字段 (Cold Storage)
    # ==========================================
    
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="扩展数据 (行为特征、历史记录等)"
    )

    # ==========================================
    # 并发控制
    # ==========================================
    
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="乐观锁版本号"
    )

    # ==========================================
    # 关系映射 (可选)
    # ==========================================
    
    # 如需反向关联可取消注释：
    # user: Mapped["UserAuth"] = relationship("UserAuth", backref="agent_memory")

    def to_dict(self) -> dict:
        """
        序列化为字典，用于 Redis 缓存和 API 返回。
        
        Returns:
            包含所有字段的字典。
        """
        return {
            "user_id": self.user_id,
            "preference_brand": self.preference_brand,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "preference_tags": self.preference_tags or [],
            "extra_data": self.extra_data or {},
            "version": self.version,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def to_natural_language(self) -> str:
        """
        将用户画像转换为自然语言摘要，供 LLM 理解。
        
        Returns:
            人类可读的偏好描述。
        """
        parts = []
        
        if self.preference_brand:
            brands = self.preference_brand.split(",")
            parts.append(f"偏好品牌: {', '.join(brands)}")
        
        if self.budget_min or self.budget_max:
            if self.budget_min and self.budget_max:
                parts.append(f"预算范围: {self.budget_min}-{self.budget_max}万元")
            elif self.budget_min:
                parts.append(f"预算下限: {self.budget_min}万元")
            elif self.budget_max:
                parts.append(f"预算上限: {self.budget_max}万元")
        
        if self.preference_tags:
            tags = self.preference_tags if isinstance(self.preference_tags, list) else []
            if tags:
                parts.append(f"偏好标签: {', '.join(tags)}")
        
        if not parts:
            return "暂无用户偏好记录"
        
        return " | ".join(parts)

    def __repr__(self) -> str:
        return (
            f"<AgentMemoryProfile(user_id={self.user_id}, "
            f"brand={self.preference_brand}, "
            f"budget={self.budget_min}-{self.budget_max}万)>"
        )
