from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"

    database_url: str = "postgresql+asyncpg://vendedor_ia:vendedor_ia@localhost:5432/vendedor_ia"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""
    evolution_webhook_secret: str = ""

    # Quantas mensagens recentes da conversa carregar como contexto do agente.
    agent_history_window: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
