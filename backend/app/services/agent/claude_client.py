from functools import lru_cache

import anthropic

from app.config import get_settings


@lru_cache
def get_anthropic_client() -> anthropic.AsyncAnthropic:
    settings = get_settings()
    if settings.anthropic_api_key:
        return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    # Sem env var: o SDK resolve credenciais via ANTHROPIC_AUTH_TOKEN / perfil `ant auth login`.
    return anthropic.AsyncAnthropic()
