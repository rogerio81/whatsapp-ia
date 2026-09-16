import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import ConversationStatus, Message, MessageDirection, MessageSender
from app.queue import enqueue_process_inbound_message
from app.schemas.evolution import EvolutionWebhookEvent
from app.services.evolution_client import parse_inbound_message
from app.services.tenancy import (
    get_or_create_active_conversation,
    get_or_create_business,
    get_or_create_customer,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

# Quanto tempo a IA fica em silêncio numa conversa depois do lojista responder manualmente.
HANDOFF_COOLDOWN_HOURS = 6


@router.post("/evolution")
async def evolution_webhook(
    event: EvolutionWebhookEvent,
    db: AsyncSession = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(default=None),
):
    settings = get_settings()
    if settings.evolution_webhook_secret and x_webhook_secret != settings.evolution_webhook_secret:
        raise HTTPException(status_code=401, detail="assinatura de webhook inválida")

    inbound = parse_inbound_message(event.event, event.data)
    if inbound is None:
        return {"status": "ignored"}

    business = await get_or_create_business(db, event.instance)
    customer = await get_or_create_customer(db, business, inbound.wa_id, inbound.pushname or "")
    conversation = await get_or_create_active_conversation(db, business, customer)

    if inbound.from_me:
        # Lojista respondeu manualmente pelo próprio celular — tratamos como sinal de
        # handoff e pausamos a IA nessa conversa por um cooldown (ver ARCHITECTURE.md,
        # seção "Handoff humano"). Nota: isso também dispara se o backend usar a mesma
        # instância para enviar mensagens fora do fluxo normal — validar contra o
        # payload real do Evolution API antes de ligar em produção.
        conversation.status = ConversationStatus.ai_paused
        conversation.ai_paused_until = datetime.now(timezone.utc) + timedelta(hours=HANDOFF_COOLDOWN_HOURS)
        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.outbound,
            sender=MessageSender.lojista,
            content=inbound.text or "",
            external_id=inbound.external_id,
            raw_payload=event.data,
        )
        db.add(message)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()  # reenvio duplicado do mesmo evento de webhook
        return {"status": "handoff"}

    message = Message(
        conversation_id=conversation.id,
        direction=MessageDirection.inbound,
        sender=MessageSender.customer,
        content=inbound.text or "",
        external_id=inbound.external_id,
        raw_payload=event.data,
    )
    db.add(message)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"status": "duplicate"}

    ai_paused = conversation.status == ConversationStatus.ai_paused and (
        conversation.ai_paused_until is not None and conversation.ai_paused_until > datetime.now(timezone.utc)
    )
    if ai_paused:
        return {"status": "ai_paused"}

    await enqueue_process_inbound_message(str(message.id))
    return {"status": "queued"}
