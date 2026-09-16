"""Loop do agente de vendas.

Loop manual (não o Tool Runner do SDK, que é pensado para um script síncrono de ponta
a ponta): aqui o histórico vive no Postgres e cada turno roda dentro de um job de
worker, então precisamos controlar explicitamente carregamento de contexto,
persistência e execução de tool contra a sessão de banco em uso.
"""

import json
import logging
from typing import Optional

from sqlalchemy import select

from app.config import get_settings
from app.models import Message, MessageSender
from app.services.agent.claude_client import get_anthropic_client
from app.services.agent.prompts import build_system_prompt
from app.services.agent.tools import TOOL_DEFINITIONS, TOOL_HANDLERS, ToolContext

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 6

# Réplica de WhatsApp raramente precisa de respostas longas; 4096 tokens dão folga
# generosa para texto + algumas tool calls sem chegar perto do teto e sem gastar à toa.
MAX_TOKENS = 4096


async def _load_history(ctx: ToolContext, window: int) -> list[dict]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == ctx.conversation.id)
        .order_by(Message.created_at.desc())
        .limit(window)
    )
    rows = list((await ctx.db.execute(stmt)).scalars())
    rows.reverse()

    history = []
    for msg in rows:
        # Mensagens do lojista (handoff manual) entram como turno "assistant" também —
        # do ponto de vista do cliente final, é a mesma "voz" da loja falando.
        role = "user" if msg.sender == MessageSender.customer else "assistant"
        history.append({"role": role, "content": msg.content})
    return history


async def run_agent_turn(ctx: ToolContext, trigger_note: Optional[str] = None) -> str:
    """`trigger_note` é usado por gatilhos internos (ex.: disparo de follow-up agendado)
    que precisam que o agente fale primeiro, sem uma mensagem nova do cliente. Não é
    persistido como mensagem do cliente — existe só para esta chamada à API."""
    settings = get_settings()
    client = get_anthropic_client()

    system_prompt = build_system_prompt(ctx.business)
    messages = await _load_history(ctx, settings.agent_history_window)
    if trigger_note:
        messages.append({"role": "user", "content": trigger_note})

    final_text = ""
    for _ in range(MAX_TOOL_ITERATIONS):
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        text_blocks = [block.text for block in response.content if block.type == "text"]
        final_text = "\n".join(text_blocks) if text_blocks else final_text

        if response.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            handler = TOOL_HANDLERS.get(block.name)
            if handler is None:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Tool desconhecida: {block.name}",
                        "is_error": True,
                    }
                )
                continue
            try:
                result = await handler(ctx, **block.input)
            except Exception as exc:  # tool handlers não devem derrubar o turno inteiro
                logger.exception("Falha executando tool %s", block.name)
                result = json.dumps({"error": str(exc)})
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result, "is_error": True}
                )
                continue
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

        messages.append({"role": "user", "content": tool_results})
    else:
        logger.warning(
            "Loop do agente atingiu MAX_TOOL_ITERATIONS (conversation_id=%s)", ctx.conversation.id
        )

    return final_text or "Desculpa, tive um problema para responder agora — já te retorno."
