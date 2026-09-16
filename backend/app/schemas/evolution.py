from typing import Any, Optional

from pydantic import BaseModel


class EvolutionWebhookEvent(BaseModel):
    """Envelope genérico dos eventos do Evolution API.

    O formato real varia por tipo de evento (`messages.upsert`, `connection.update`, ...);
    mantemos `data` como dict livre e extraímos o que precisamos em `services/evolution_client.py`.
    """

    event: str
    instance: str
    data: dict[str, Any]


class InboundMessage(BaseModel):
    """Forma normalizada de uma mensagem de texto recebida, extraída do payload bruto."""

    external_id: str
    wa_id: str
    from_me: bool
    text: Optional[str] = None
    pushname: Optional[str] = None
