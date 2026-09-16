import enum
from datetime import date
from typing import Optional

from sqlalchemy import JSON, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class BusinessStatus(str, enum.Enum):
    onboarding = "onboarding"
    active = "active"
    paused = "paused"


class Business(UUIDPKMixin, TimestampMixin, Base):
    """Um lojista. Tudo no sistema é isolado por business_id (multi-tenant)."""

    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[BusinessStatus] = mapped_column(
        default=BusinessStatus.onboarding, server_default=BusinessStatus.onboarding.value
    )

    # Identifica a instância do Evolution API (um número de WhatsApp por lojista).
    evolution_instance_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    timezone: Mapped[str] = mapped_column(String(50), default="America/Sao_Paulo")

    # Perfil coletado no onboarding conversacional — ver PRD seção 04.
    business_hours: Mapped[dict] = mapped_column(JSON, default=dict)
    delivery_info: Mapped[str] = mapped_column(Text, default="")
    payment_methods: Mapped[dict] = mapped_column(JSON, default=dict)

    # Horário (0-23, no timezone do lojista) em que o resumo diário de oportunidades é enviado.
    daily_summary_hour: Mapped[int] = mapped_column(Integer, default=8)
    last_daily_summary_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # JID de WhatsApp para onde mandar o resumo diário. Como o Evolution API opera com o
    # próprio número do lojista (ver ARCHITECTURE.md), isso normalmente é "mensagem para
    # si mesmo" (Note to Self) — precisa validar se o Evolution API/Baileys suporta esse
    # envio antes de contar com isso em produção; é um ponto em aberto do desenho.
    owner_wa_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
