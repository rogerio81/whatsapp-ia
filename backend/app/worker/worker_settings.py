from arq.connections import RedisSettings
from arq.cron import cron

from app.config import get_settings
from app.worker.tasks import process_inbound_message, send_daily_summary_all, send_followup

settings = get_settings()


class WorkerSettings:
    functions = [process_inbound_message, send_followup]
    cron_jobs = [
        # Checa a cada 15 min; a lógica interna decide se é a hora certa (timezone do
        # lojista) e evita duplicar envio no mesmo dia. Ver worker/tasks.py.
        cron(send_daily_summary_all, minute={0, 15, 30, 45}),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
