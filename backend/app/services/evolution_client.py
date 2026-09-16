from typing import Any, Optional

import httpx

from app.config import get_settings
from app.schemas.evolution import InboundMessage

settings = get_settings()


def parse_inbound_message(event: str, data: dict[str, Any]) -> Optional[InboundMessage]:
    """Normaliza o payload de um evento `messages.upsert` do Evolution API.

    O shape exato depende da versão do Evolution API — este parser cobre o formato
    padrão (Baileys) e deve ser ajustado contra o payload real assim que a instância
    estiver rodando. Retorna None para eventos que não são mensagem de texto.
    """
    if event != "messages.upsert":
        return None

    key = data.get("key") or {}
    message = data.get("message") or {}

    text = (
        message.get("conversation")
        or (message.get("extendedTextMessage") or {}).get("text")
    )
    if text is None:
        return None

    external_id = key.get("id")
    wa_id = key.get("remoteJid")
    if not external_id or not wa_id:
        return None

    return InboundMessage(
        external_id=external_id,
        wa_id=wa_id,
        from_me=bool(key.get("fromMe", False)),
        text=text,
        pushname=data.get("pushName"),
    )


class EvolutionClient:
    """Cliente HTTP para o Evolution API — uma instância por lojista (número de WhatsApp)."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or settings.evolution_api_url).rstrip("/")
        self.api_key = api_key or settings.evolution_api_key

    def _headers(self) -> dict[str, str]:
        return {"apikey": self.api_key, "Content-Type": "application/json"}

    async def send_text(self, instance: str, to: str, text: str) -> dict[str, Any]:
        url = f"{self.base_url}/message/sendText/{instance}"
        payload = {"number": to, "text": text}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()
