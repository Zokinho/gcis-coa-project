"""Celery tasks and dispatch helpers for email notifications."""

import asyncio
import logging
from threading import Thread

from backend.celery_app import celery

logger = logging.getLogger(__name__)


# ── Celery tasks ──────────────────────────────────────────────────


@celery.task(bind=True, max_retries=1, default_retry_delay=15)
def send_job_ready_notification(self, job_id: str, filename: str, product_name: str) -> bool:
    """Send a 'job ready for review' email notification."""
    from backend.services.email_notification import notify_job_ready

    try:
        return asyncio.run(notify_job_ready(job_id, filename, product_name))
    except Exception as e:
        logger.exception("[%s] Job-ready notification task failed", job_id)
        if hasattr(self, "request") and self.request.id is not None:
            raise self.retry(exc=e)
        return False


@celery.task(bind=True, max_retries=1, default_retry_delay=15)
def send_new_email_notification(
    self,
    ingestion_id: str,
    subject: str,
    sender: str,
    attachment_count: int,
    coa_count: int,
) -> bool:
    """Send a 'new email ingested' email notification."""
    from backend.services.email_notification import notify_new_email

    try:
        return asyncio.run(notify_new_email(ingestion_id, subject, sender, attachment_count, coa_count))
    except Exception as e:
        logger.exception("[%s] New-email notification task failed", ingestion_id)
        if hasattr(self, "request") and self.request.id is not None:
            raise self.retry(exc=e)
        return False


# ── Dispatch helpers (Celery → Thread fallback) ───────────────────


def _run_job_ready_in_thread(job_id: str, filename: str, product_name: str) -> None:
    from backend.services.email_notification import notify_job_ready

    asyncio.run(notify_job_ready(job_id, filename, product_name))


def _run_new_email_in_thread(
    ingestion_id: str, subject: str, sender: str, attachment_count: int, coa_count: int,
) -> None:
    from backend.services.email_notification import notify_new_email

    asyncio.run(notify_new_email(ingestion_id, subject, sender, attachment_count, coa_count))


def dispatch_job_ready_notification(job_id: str, filename: str, product_name: str) -> None:
    """Send to Celery, fall back to thread if Redis is unreachable."""
    try:
        send_job_ready_notification.delay(job_id, filename, product_name)
        logger.info("[%s] Job-ready notification dispatched to Celery", job_id)
    except Exception:
        logger.info("[%s] Celery unavailable, sending job-ready notification in thread", job_id)
        Thread(target=_run_job_ready_in_thread, args=(job_id, filename, product_name), daemon=True).start()


def dispatch_new_email_notification(
    ingestion_id: str,
    subject: str,
    sender: str,
    attachment_count: int,
    coa_count: int,
) -> None:
    """Send to Celery, fall back to thread if Redis is unreachable."""
    try:
        send_new_email_notification.delay(ingestion_id, subject, sender, attachment_count, coa_count)
        logger.info("[%s] New-email notification dispatched to Celery", ingestion_id)
    except Exception:
        logger.info("[%s] Celery unavailable, sending new-email notification in thread", ingestion_id)
        Thread(
            target=_run_new_email_in_thread,
            args=(ingestion_id, subject, sender, attachment_count, coa_count),
            daemon=True,
        ).start()
