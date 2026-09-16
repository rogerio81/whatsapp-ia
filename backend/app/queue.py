from datetime import datetime
from typing import Optional

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings

_pool: Optional[ArqRedis] = None


async def get_redis_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def enqueue_process_inbound_message(message_id: str) -> None:
    pool = await get_redis_pool()
    await pool.enqueue_job("process_inbound_message", message_id)


async def enqueue_followup(followup_id: str, due_at: datetime) -> None:
    pool = await get_redis_pool()
    await pool.enqueue_job("send_followup", followup_id, _defer_until=due_at)
