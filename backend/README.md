# Vendedor IA — backend

FastAPI + SQLAlchemy (async) + Claude API (tool use) + arq (filas/agendamento). Ver
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) para o desenho completo.

## Rodando com Docker (recomendado)

```bash
cp backend/.env.example backend/.env
# edite backend/.env: pelo menos ANTHROPIC_API_KEY

docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d api worker
```

A API sobe em `http://localhost:8000` (`GET /health`). O Evolution API (gateway do
WhatsApp) é outro serviço do `docker-compose.yml`, mas exige configuração própria
(criar instância, escanear QR code) antes de gerar tráfego real — ver
[doc.evolution-api.com](https://doc.evolution-api.com).

## Rodando local (sem Docker)

Requer Python 3.11+, Postgres e Redis rodando.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # edite com sua DATABASE_URL/REDIS_URL/ANTHROPIC_API_KEY

alembic upgrade head
uvicorn app.main:app --reload         # API
arq app.worker.worker_settings.WorkerSettings   # worker (outro terminal)
```

## Simular mensagens sem WhatsApp real

Enquanto não há uma instância do Evolution API conectada, dá pra testar o agente
inteiro (webhook → fila → Claude com tool use → resposta) direto pela API.

1. Popule um negócio de teste com catálogo:
   ```bash
   python -m scripts.seed_demo
   ```
   Cria a instância `loja-teste` com duas peças cadastradas (blusa preta P/M/G,
   calça jeans 38/40). Rodar de novo é seguro — não duplica.

2. Simule uma mensagem de cliente chegando:
   ```bash
   curl -X POST http://localhost:8000/webhooks/evolution \
     -H "Content-Type: application/json" \
     -d '{
       "event": "messages.upsert",
       "instance": "loja-teste",
       "data": {
         "key": {"id": "MSG1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": false},
         "message": {"conversation": "Oi, quanto custa a blusa preta?"},
         "pushName": "Ana"
       }
     }'
   ```
   O backend cria a cliente automaticamente, enfileira o processamento, e o worker
   chama o Claude (precisa de `ANTHROPIC_API_KEY` válida) e tenta enviar a resposta
   via Evolution API — sem uma instância real conectada, o envio final falha, mas dá
   pra ver a resposta do agente nos logs do worker (`docker compose logs -f worker`).

## Testes

```bash
pytest
```

Os testes usam SQLite em arquivo (não Postgres) e não chamam a API da Anthropic nem o
Evolution API de verdade — cobrem o wiring (rotas, modelos, deduplicação de webhook,
handoff), não o comportamento do agente.

## Estrutura

```
app/
├── main.py                 # FastAPI app
├── config.py                # settings (.env)
├── db.py                    # engine/session SQLAlchemy async
├── models/                  # tabelas (SQLAlchemy 2.0)
├── schemas/                 # payloads Pydantic (webhook do Evolution API)
├── api/routes/               # health, webhooks
├── services/
│   ├── evolution_client.py   # HTTP client + parser do payload do Evolution API
│   ├── tenancy.py             # get_or_create business/customer/conversation
│   └── agent/                 # prompt, tools, loop do agente (Claude)
└── worker/
    ├── tasks.py               # jobs do arq (processa mensagem, follow-up, resumo diário)
    └── worker_settings.py

alembic/                     # migrações (assíncrono)
scripts/
└── seed_demo.py             # popula negócio + catálogo de teste (ver seção abaixo)
tests/
```

## O que ainda é stub / decisão em aberto

Tudo listado aqui está sinalizado com comentário `TODO`/nota no código correspondente:

- **Gateway de pagamento** (`generate_payment_link`): retorna um Pix fake. Trocar pelo
  gateway real (Asaas/Pagar.me/Mercado Pago) é o próximo passo de maior impacto —
  sem isso não há confirmação de pagamento de verdade.
- **Cálculo de frete** (`calculate_shipping`): regra fixa (R$12/R$25), não é frete real.
- **Resumo diário para o lojista**: como o Evolution API opera com o próprio número do
  lojista, o envio depende de `Business.owner_wa_id` (mensagem "para si mesmo") — não
  validado contra uma instância real ainda. Ver `docs/ARCHITECTURE.md`.
- **Parser do webhook do Evolution API** (`parse_inbound_message`): cobre o formato
  padrão de `messages.upsert` (Baileys); ajustar contra o payload real assim que a
  instância estiver conectada.
