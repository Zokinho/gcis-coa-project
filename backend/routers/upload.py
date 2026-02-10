"""Upload router — accepts CoA PDF uploads and kicks off processing."""

import logging
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import CoAJob, JobResponse
from backend.tasks.dispatch import send_process_coa

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=JobResponse)
async def upload_coa(
    file: UploadFile = File(...),
    client_name: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a CoA PDF for processing.

    Saves the file, creates a job record, and starts processing in a background thread.
    Optionally accepts a client_name to pre-assign the product to a client.
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
    job = CoAJob(filename=file.filename, client_name=client_name or None)
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info("Created job %s for file %s", job.id, file.filename)

    # Dispatch to Celery (falls back to threading if Redis unavailable)
    send_process_coa(job.id)

    return job
