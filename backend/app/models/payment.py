import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    failed = "failed"


class Payment(UUIDPKMixin, TimestampMixin, Base):
    """`status` só pode virar `confirmed` a partir do webhook do gateway
    (ver ARCHITECTURE.md — requisito não-negociável). Nunca por escrita direta."""

    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    status: Mapped[PaymentStatus] = mapped_column(
        default=PaymentStatus.pending, server_default=PaymentStatus.pending.value
    )
    amount: Mapped[Numeric] = mapped_column(Numeric(10, 2))
    raw_webhook_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
