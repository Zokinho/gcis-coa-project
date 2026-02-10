"""Celery tasks and dispatch helpers for Evernote imports."""

import logging
from threading import Thread

from backend.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=1, default_retry_delay=30)
def run_evernote_import(self, note_guid: str, client_name: str | None = None) -> str | None:
    """Import PDFs and photos from an Evernote note."""
    from backend.services.evernote_import import import_evernote_note

    try:
        return import_evernote_note(note_guid, client_name)
    except Exception as e:
        logger.exception("Evernote import task failed for note %s", note_guid)
        if hasattr(self, "request") and self.request.id is not None:
            raise self.retry(exc=e)
        return None


def dispatch_evernote_import(note_guid: str, client_name: str | None = None) -> None:
    """Send to Celery, fall back to thread if Redis is unreachable."""
    try:
        run_evernote_import.delay(note_guid, client_name)
        logger.info("Evernote import dispatched to Celery for note %s", note_guid)
    except Exception:
        logger.info("Celery unavailable, running Evernote import in thread for note %s", note_guid)
        from backend.services.evernote_import import import_evernote_note

        Thread(target=import_evernote_note, args=(note_guid, client_name), daemon=True).start()
