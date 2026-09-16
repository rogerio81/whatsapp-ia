import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class FollowupStatus(str, enum.Enum):
    scheduled = "scheduled"
    sent = "sent"
    canceled = "canceled"


class Followup(UUIDPKMixin, TimestampMixin, Base):
    """Criado pela tool `schedule_followup` quando o cliente diz algo como
    'vou pensar'. Um job atrasado no arq dispara o envio em `due_at`."""

    __tablename__ = "followups"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))

    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[FollowupStatus] = mapped_column(
        default=FollowupStatus.scheduled, server_default=FollowupStatus.scheduled.value
    )
    # Contexto livre que o agente grava para lembrar do que tratar no retorno
    # (ex.: "cliente viu blusa preta M, R$ 89,90, perguntou frete").
    context: Mapped[str] = mapped_column(Text, default="")
