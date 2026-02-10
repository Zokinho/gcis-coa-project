"""Celery task for periodic email inbox polling."""

import logging

from backend.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="backend.tasks.email_tasks.poll_inbox")
def poll_inbox() -> int:
    """Poll the IMAP inbox for new CoA emails. Called by Celery Beat on schedule."""
    from backend.services.email_ingestion import poll_inbox_once

    logger.info("Celery Beat: polling inbox")
    return poll_inbox_once()
