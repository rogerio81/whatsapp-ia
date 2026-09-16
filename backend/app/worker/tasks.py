import logging
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app import queue
from app.db import session_scope
from app.models import (
    Business,
    BusinessStatus,
    Conversation,
    Customer,
    Followup,
    FollowupStatus,
    Message,
    MessageDirection,
    MessageSender,
    Opportunity,
    OpportunityStatus,
)
from app.services.agent.orchestrator import run_agent_turn
from app.services.agent.tools import ToolContext
from app.services.evolution_client import EvolutionClient

logger = logging.getLogger(__name__)


async def process_inbound_message(ctx: dict, message_id: str) -> None:
    """Roda o turno do agente para uma mensagem recebida e envia a resposta."""
    async with session_scope() as db:
        message = await db.get(Message, uuid.UUID(message_id))
        if message is None:
            logger.warning("process_inbound_message: mensagem %s não encontrada", message_id)
            return

        conversation = await db.get(Conversation, message.conversation_id)
        business = await db.get(Business, conversation.business_id)
        customer = await db.get(Customer, conversation.customer_id)

        tool_ctx = ToolContext(
            db=db,
            business=business,
            customer=customer,
            conversation=conversation,
            enqueue_followup=lambda fid, due: queue.enqueue_followup(str(fid), due),
        )

        reply_text = await run_agent_turn(tool_ctx)

        reply = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.outbound,
            sender=MessageSender.ai,
            content=reply_text,
        )
        db.add(reply)
        await db.commit()

    client = EvolutionClient()
    await client.send_text(instance=business.evolution_instance_name, to=customer.wa_id, text=reply_text)


async def send_followup(ctx: dict, followup_id: str) -> None:
    """Dispara um follow-up agendado por `schedule_followup`."""
    async with session_scope() as db:
        followup = await db.get(Followup, uuid.UUID(followup_id))
        if followup is None or followup.status != FollowupStatus.scheduled:
            return

        conversation = await db.get(Conversation, followup.conversation_id)
        business = await db.get(Business, followup.business_id)
        customer = await db.get(Customer, followup.customer_id)

        tool_ctx = ToolContext(
            db=db,
            business=business,
            customer=customer,
            conversation=conversation,
            enqueue_followup=lambda fid, due: queue.enqueue_followup(str(fid), due),
        )

        trigger_note = (
            "[instrução interna, não é mensagem do cliente] Está na hora de retomar o "
            f"contato combinado. Contexto salvo: {followup.context}. Escreva a mensagem de "
            "follow-up para o cliente agora, com tom natural, sem parecer cobrança."
        )
        reply_text = await run_agent_turn(tool_ctx, trigger_note=trigger_note)

        reply = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.outbound,
            sender=MessageSender.ai,
            content=reply_text,
        )
        db.add(reply)
        followup.status = FollowupStatus.sent
        await db.commit()

    client = EvolutionClient()
    await client.send_text(instance=business.evolution_instance_name, to=customer.wa_id, text=reply_text)


def _format_daily_summary(counts: dict[OpportunityStatus, int]) -> str:
    quoted = counts.get(OpportunityStatus.quoted_no_purchase, 0)
    vanished = counts.get(OpportunityStatus.vanished, 0)
    repurchase = counts.get(OpportunityStatus.repurchase_window, 0)
    total = quoted + vanished + repurchase
    return (
        f"Bom dia! Hoje você tem {total} oportunidades que merecem atenção:\n\n"
        f"🔴 {quoted} clientes pediram orçamento e não compraram\n"
        f"🟡 {vanished} clientes demonstraram interesse e desapareceram\n"
        f"🟢 {repurchase} clientes estão próximos de comprar de novo\n\n"
        "Quer que eu cuide deles? Responda \"cuidar\" para eu iniciar o contato."
    )


async def send_daily_summary_all(ctx: dict) -> None:
    """Job de cron (ver worker_settings.py). Roda a cada 15 min e dispara o resumo só
    para o negócio cujo horário configurado (no timezone dele) bate com a hora local
    atual, uma vez por dia — controlado por `last_daily_summary_date`."""
    now_utc = datetime.now(timezone.utc)

    async with session_scope() as db:
        businesses = list(
            (await db.execute(select(Business).where(Business.status == BusinessStatus.active))).scalars()
        )

        for business in businesses:
            try:
                local_now = now_utc.astimezone(ZoneInfo(business.timezone))
            except Exception:
                logger.warning("Timezone inválido para business %s: %s", business.id, business.timezone)
                continue

            already_sent_today = business.last_daily_summary_date == local_now.date()
            if local_now.hour != business.daily_summary_hour or already_sent_today:
                continue

            if not business.owner_wa_id:
                logger.info("Business %s sem owner_wa_id configurado — pulando resumo diário", business.id)
                continue

            stmt = select(Opportunity).where(
                Opportunity.business_id == business.id,
                Opportunity.status != OpportunityStatus.resolved,
                Opportunity.resolved_at.is_(None),
            )
            opportunities = list((await db.execute(stmt)).scalars())
            counts: dict[OpportunityStatus, int] = {}
            for opp in opportunities:
                counts[opp.status] = counts.get(opp.status, 0) + 1

            business.last_daily_summary_date = local_now.date()
            await db.commit()

            if not opportunities:
                continue

            text = _format_daily_summary(counts)
            client = EvolutionClient()
            await client.send_text(instance=business.evolution_instance_name, to=business.owner_wa_id, text=text)
