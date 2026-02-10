"""Dispatch helper — routes CoA processing to Celery or falls back to threading."""

import logging
from threading import Thread

logger = logging.getLogger(__name__)


def send_process_coa(job_id: str) -> None:
    """Send process_coa to Celery, fall back to threading if Redis is unreachable."""
    try:
        from backend.tasks.process_coa import process_coa

        process_coa.delay(job_id)
        logger.info("[%s] Dispatched to Celery", job_id)
    except Exception:
        logger.info("[%s] Celery unavailable, falling back to thread", job_id)
        from backend.tasks.process_coa import process_coa as _fn

        Thread(target=_fn, args=(job_id,), daemon=True).start()
