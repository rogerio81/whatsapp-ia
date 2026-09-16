import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Customer(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("business_id", "wa_id", name="uq_customer_business_wa_id"),)

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)

    # JID do WhatsApp (ex.: 5511999999999@s.whatsapp.net) — identifica o cliente na instância.
    wa_id: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255), default="")
