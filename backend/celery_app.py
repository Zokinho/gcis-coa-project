"""Celery application — broker and task configuration."""

from celery import Celery
from backend.config import settings

celery = Celery(
    "gcis_coa",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # one task at a time (AI calls are slow)
    beat_schedule={},
)

# Periodic email polling (only when IMAP is fully configured)
if settings.email_ingestion_enabled and settings.imap_host and settings.imap_user:
    celery.conf.beat_schedule["poll-email-inbox"] = {
        "task": "backend.tasks.email_tasks.poll_inbox",
        "schedule": settings.imap_poll_interval_seconds,
    }

# Auto-discover tasks in backend.tasks package
celery.autodiscover_tasks(["backend.tasks"])
