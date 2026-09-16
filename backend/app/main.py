from fastapi import FastAPI

from app.api.routes import health, webhooks
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="Vendedor IA — backend")

app.include_router(health.router)
app.include_router(webhooks.router)
