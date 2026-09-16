import os
from pathlib import Path

_TEST_DB_PATH = Path(__file__).parent / "_test.db"

# Precisa rodar antes de qualquer `import app...` (inclusive dos módulos de teste) —
# por isso fica no nível do módulo, não numa fixture. pytest importa conftest.py antes
# de coletar os arquivos de teste do diretório. Usamos arquivo (não `:memory:`) porque
# cada conexão do pool assíncrono veria um banco em memória diferente.
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB_PATH}")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest_asyncio  # noqa: E402


@pytest_asyncio.fixture(autouse=True, scope="session")
async def _setup_db():
    from app.db import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
