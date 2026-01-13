from enum import Enum
from carfast.app.models.user import TimestampMixin, Base
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# ==========================================
# 5. 交易订单域 (Trade & Order Domain)
# 提示: 金融级数据，必须留在PG
# ==========================================

class OrderStatus(int, Enum):
    PENDING = 0  # 待支付
    PAID = 1  # 已支付
    CANCELLED = 2  # 已取消
    REFUNDED = 3  # 已退款


class TradeOrder(Base, TimestampMixin):
    """
    表名: trade_order
    功能: 核心订单表
    """
    __tablename__ = "trade_order"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="业务订单号")
    user_id: Mapped[int] = mapped_column(ForeignKey("uc_user_auth.id"), index=True)

    order_type: Mapped[str] = mapped_column(String(20), comment="类型: deposit(定金)/member(会员)")
    total_amount: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), comment="金额(元)")
    status: Mapped[OrderStatus] = mapped_column(Integer, default=OrderStatus.PENDING)

    # 业务关联 (多态关联的简化版: 存ID和Json快照)
    related_item_id: Mapped[Optional[str]] = mapped_column(String(50), comment="关联商品ID(如car_id)")
    snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, comment="下单时商品快照")


class TradePaymentLog(Base, TimestampMixin):
    """
    表名: trade_payment_log
    功能: 支付流水对账
    """
    __tablename__ = "trade_payment_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("trade_order.id"), index=True)

    channel: Mapped[str] = mapped_column(String(20), comment="alipay/wechat")
    trade_no: Mapped[str] = mapped_column(String(64), index=True, comment="三方流水号")
    amount: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2))
    pay_time: Mapped[datetime] = mapped_column(DateTime)


