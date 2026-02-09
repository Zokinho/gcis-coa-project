"""Upload router — accepts CoA PDF uploads and kicks off processing."""

import logging
import shutil
from threading import Thread

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import CoAJob, JobResponse
from backend.tasks.process_coa import process_coa

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=JobResponse)
async def upload_coa(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a CoA PDF for processing.

    Saves the file, creates a job record, and starts processing in a background thread.
    In production, this would use Celery; for Phase 1 we use threading.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save uploaded file
    upload_path = settings.uploads_path / file.filename
    try:
        with open(upload_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.error("Failed to save upload: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Create job record
    job = CoAJob(filename=file.filename)
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info("Created job %s for file %s", job.id, file.filename)

    # Start processing in background thread (Phase 1 — no Celery yet)
    thread = Thread(target=process_coa, args=(job.id,), daemon=True)
    thread.start()

    return job
