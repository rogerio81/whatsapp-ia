import enum
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class OrderStatus(str, enum.Enum):
    pending = "pending"
    awaiting_payment = "awaiting_payment"
    paid = "paid"
    canceled = "canceled"


class Order(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)

    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.pending, server_default=OrderStatus.pending.value)
    shipping_address: Mapped[str] = mapped_column(Text, default="")
    shipping_cost: Mapped[Numeric] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[Numeric] = mapped_column(Numeric(10, 2), default=0)


class OrderItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    product_variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Numeric] = mapped_column(Numeric(10, 2))
