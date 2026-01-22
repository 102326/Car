"""
模型导出模块
统一导出所有 SQLAlchemy 模型和 Base
"""
from app.models.user import (
    Base,
    TimestampMixin,
    UserAuth,
    UserProfile,
    RealnameVerify,
    UserAddress
)

from app.models.car import (
    CarBrand,
    CarSeries,
    CarModel,
    CarDealer
)

from app.models.Content_Resource import (
    PostType,
    CMSPost,
    CMSComment,
    SysFileResource,
    UsedCarListing,
    NESubsidyPolicy
)

from app.models.trade import (
    OrderStatus,
    TradeOrder,
    TradePaymentLog
)

from app.models.systemDomain import (
    AppVersion,
    AIChatSession
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    
    # User Domain
    "UserAuth",
    "UserProfile",
    "RealnameVerify",
    "UserAddress",
    
    # Car Domain
    "CarBrand",
    "CarSeries",
    "CarModel",
    "CarDealer",
    
    # Content & Resource Domain
    "PostType",
    "CMSPost",
    "CMSComment",
    "SysFileResource",
    "UsedCarListing",
    "NESubsidyPolicy",
    
    # Trade Domain
    "OrderStatus",
    "TradeOrder",
    "TradePaymentLog",
    
    # System Domain
    "AppVersion",
    "AIChatSession",
]
