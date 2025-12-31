from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "app",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.sms_tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        "assign-pending-messages": {
            "task": "app.tasks.sms_tasks.assign_pending_messages",
            "schedule": 30.0,  # Cada 30 segundos
        },
        "retry-failed-messages": {
            "task": "app.tasks.sms_tasks.retry_failed_messages",
            "schedule": 300.0,  # Cada 5 minutos
        },
        "cleanup-offline-devices": {
            "task": "app.tasks.sms_tasks.cleanup_offline_devices",
            "schedule": 60.0,  # Cada minuto
        },
        "reset-monthly-quotas": {
            "task": "app.tasks.sms_tasks.reset_monthly_quotas",
            "schedule": 86400.0,  # Diario a las 00:00 UTC
        },
    },
)
