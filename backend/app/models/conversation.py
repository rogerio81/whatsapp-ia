import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class ConversationStatus(str, enum.Enum):
    active = "active"
    # Lojista respondeu manualmente pelo celular — IA fica em silêncio até o cooldown passar.
    ai_paused = "ai_paused"
    closed = "closed"


class Conversation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)

    status: Mapped[ConversationStatus] = mapped_column(
        default=ConversationStatus.active, server_default=ConversationStatus.active.value
    )
    ai_paused_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class MessageDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class MessageSender(str, enum.Enum):
    customer = "customer"
    ai = "ai"
    lojista = "lojista"


class Message(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), index=True)

    direction: Mapped[MessageDirection] = mapped_column()
    sender: Mapped[MessageSender] = mapped_column()
    content: Mapped[str] = mapped_column(Text)

    # ID da mensagem no Evolution API — chave de deduplicação para webhooks reenviados.
    external_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
