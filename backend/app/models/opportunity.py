import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class OpportunityStatus(str, enum.Enum):
    quoted_no_purchase = "quoted_no_purchase"  # 🔴 pediu orçamento e não comprou
    vanished = "vanished"  # 🟡 demonstrou interesse e sumiu
    repurchase_window = "repurchase_window"  # 🟢 provável janela de recompra
    resolved = "resolved"


class Opportunity(UUIDPKMixin, TimestampMixin, Base):
    """Criada pela tool `mark_opportunity`, chamada pelo próprio agente durante a
    conversa — não é um job de classificação separado. Ver ARCHITECTURE.md."""

    __tablename__ = "opportunities"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)

    status: Mapped[OpportunityStatus] = mapped_column()
    reason: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
