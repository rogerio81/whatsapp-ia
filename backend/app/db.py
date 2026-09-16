from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependência do FastAPI: uma sessão por request."""
    async with async_session_factory() as session:
        yield session


def session_scope() -> AsyncSession:
    """Uso fora do FastAPI (workers do arq): `async with session_scope() as db:`."""
    return async_session_factory()
