"""CoA processing pipeline — runs the full extraction workflow for an uploaded PDF."""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from backend.celery_app import celery
from backend.config import settings
from backend.database import SessionLocal
from backend.models import CoAJob, JobStatus, RedactionRegion, Confidence
from backend.services.pdf_unlock import unlock_pdf
from backend.services.pdf_to_images import convert_pdf_to_images
from backend.services.ai_extractor import extract_all_pages
from backend.services.merger import merge_extractions, generate_tags
from backend.services.redactor import apply_redactions
from backend.services.publisher import publish_product

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def process_coa(self, job_id: str) -> None:
    """Run the full CoA processing pipeline for a given job.

    Steps:
    1. Unlock PDF (remove owner password if present)
    2. Convert pages to images
    3. Send each page to Claude Vision API
    4. Merge extraction results across pages
    5. Save redaction regions to DB
    6. Apply redactions and generate preview PDF
    7. Publish product record
    """
    db: Session = SessionLocal()
    try:
        job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
        if not job:
            logger.error("Job not found: %s", job_id)
            return

        _update_status(db, job, JobStatus.processing)

        upload_path = settings.uploads_path / job.filename
        if not upload_path.exists():
            _fail(db, job, f"Upload file not found: {upload_path}")
            return

        # Set up working directory for this job
        work_dir = settings.working_path / job.id
        work_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Unlock PDF
        logger.info("[%s] Step 1: Unlocking PDF", job.id)
        unlocked_path = work_dir / "unlocked.pdf"
        success, was_locked, error = unlock_pdf(upload_path, unlocked_path)

        if not success:
            _fail(db, job, error or "PDF unlock failed", flagged=True)
            return

        # Step 2: Convert to images
        logger.info("[%s] Step 2: Converting to images", job.id)
        page_images = convert_pdf_to_images(unlocked_path, work_dir)
        job.page_count = len(page_images)
        db.commit()

        # Step 3: AI extraction
        logger.info("[%s] Step 3: AI extraction (%d pages)", job.id, len(page_images))
        page_results = extract_all_pages(page_images)

        # Step 4: Merge results
        logger.info("[%s] Step 4: Merging results", job.id)
        merged = merge_extractions(page_results)
        tags = generate_tags(merged)

        # Step 5: Save redaction regions to DB
        logger.info("[%s] Step 5: Saving %d redaction regions", job.id, len(merged.redaction_regions))
        for region_data in merged.redaction_regions:
            region = RedactionRegion(
                job_id=job.id,
                page=region_data.get("page", 0),
                x_pct=region_data.get("x_pct", 0),
                y_pct=region_data.get("y_pct", 0),
                w_pct=region_data.get("w_pct", 0),
                h_pct=region_data.get("h_pct", 0),
                reason=region_data.get("reason", "Client info"),
                confidence=Confidence(region_data.get("confidence", "high")),
                approved=True,
            )
            db.add(region)
        db.commit()

        # Step 6: Apply redactions
        logger.info("[%s] Step 6: Applying redactions", job.id)
        redacted_dir = settings.redacted_path / job.id
        redacted_dir.mkdir(parents=True, exist_ok=True)
        redacted_pdf_path = redacted_dir / "preview.pdf"

        apply_redactions(page_images, merged.redaction_regions, redacted_pdf_path)

        # Step 7: Publish product
        logger.info("[%s] Step 7: Publishing product record", job.id)
        product = publish_product(db, job, merged, tags, redacted_pdf_path)

        logger.info("[%s] Pipeline complete — product %s (%s)", job.id, product.name, product.id)

        # Dispatch admin notification
        try:
            from backend.tasks.notification_tasks import dispatch_job_ready_notification
            dispatch_job_ready_notification(job.id, job.filename, product.name if product else "")
        except Exception:
            logger.exception("[%s] Failed to dispatch review notification", job.id)

    except Exception as e:
        logger.exception("[%s] Pipeline error: %s", job_id, e)
        try:
            job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
            if job:
                _fail(db, job, str(e))
        except Exception:
            logger.exception("Failed to update job status on error")

        # Retry transient errors via Celery (only when running as a Celery task)
        if hasattr(self, "request") and self.request.id is not None:
            raise self.retry(exc=e)
    finally:
        db.close()


def _update_status(db: Session, job: CoAJob, status: JobStatus) -> None:
    job.status = status
    db.commit()
    logger.info("[%s] Status → %s", job.id, status.value)


def _fail(db: Session, job: CoAJob, message: str, flagged: bool = False) -> None:
    job.status = JobStatus.flagged if flagged else JobStatus.error
    job.error_message = message
    db.commit()
    logger.error("[%s] %s: %s", job.id, job.status.value, message)
