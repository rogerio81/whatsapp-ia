from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.main import app

WEBHOOK_PAYLOAD = {
    "event": "messages.upsert",
    "instance": "loja-teste",
    "data": {
        "key": {"id": "MSG1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "message": {"conversation": "Quanto custa a blusa preta?"},
        "pushName": "Ana",
    },
}


async def test_webhook_creates_tenant_and_enqueues_job(monkeypatch):
    enqueue_mock = AsyncMock()
    monkeypatch.setattr("app.api.routes.webhooks.enqueue_process_inbound_message", enqueue_mock)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhooks/evolution", json=WEBHOOK_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"status": "queued"}
    enqueue_mock.assert_awaited_once()


async def test_webhook_dedupes_repeated_external_id(monkeypatch):
    monkeypatch.setattr("app.api.routes.webhooks.enqueue_process_inbound_message", AsyncMock())

    payload = {**WEBHOOK_PAYLOAD, "data": {**WEBHOOK_PAYLOAD["data"], "key": {**WEBHOOK_PAYLOAD["data"]["key"], "id": "MSG-DUP"}}}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/webhooks/evolution", json=payload)
        second = await client.post("/webhooks/evolution", json=payload)

    assert first.json() == {"status": "queued"}
    assert second.json() == {"status": "duplicate"}


async def test_webhook_handoff_on_from_me():
    payload = {
        "event": "messages.upsert",
        "instance": "loja-teste",
        "data": {
            "key": {"id": "MSG-HANDOFF", "remoteJid": "5511988887777@s.whatsapp.net", "fromMe": True},
            "message": {"conversation": "Oi, aqui é a dona da loja"},
        },
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhooks/evolution", json=payload)

    assert response.json() == {"status": "handoff"}
