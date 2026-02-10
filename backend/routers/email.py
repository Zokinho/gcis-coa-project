"""Email ingestion router — manage ingested emails, attachments, and client confirmation."""

import logging
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.auth import get_admin_user
from backend.config import settings
from backend.database import get_db
from backend.models import (
    AttachmentType,
    CoAJob,
    EmailAttachment,
    EmailAttachmentReclassify,
    EmailAttachmentResponse,
    EmailClientConfirm,
    EmailIngestion,
    EmailIngestionResponse,
    EmailIngestionStatus,
    JobStatus,
    Product,
)
from backend.services.email_ingestion import (
    classify_attachment,
    image_to_pdf,
    poll_inbox_once,
)
from backend.tasks.process_coa import process_coa

logger = logging.getLogger(__name__)
router = APIRouter(tags=["email"])


# ── List emails ──────────────────────────────────────────────────


@router.get("/api/email/ingestions", response_model=list[EmailIngestionResponse])
async def list_email_ingestions(
    status: EmailIngestionStatus | None = None,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """List email ingestions, optionally filtered by status."""
    q = db.query(EmailIngestion).order_by(EmailIngestion.created_at.desc())
    if status:
        q = q.filter(EmailIngestion.status == status)
    return q.all()


# ── Single email ─────────────────────────────────────────────────


@router.get("/api/email/ingestions/{ingestion_id}", response_model=EmailIngestionResponse)
async def get_email_ingestion(
    ingestion_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Get a single email ingestion with its attachments."""
    ingestion = db.query(EmailIngestion).filter(EmailIngestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Email ingestion not found")
    return ingestion


# ── Confirm / override client ────────────────────────────────────


@router.patch("/api/email/ingestions/{ingestion_id}/client", response_model=EmailIngestionResponse)
async def confirm_email_client(
    ingestion_id: str,
    body: EmailClientConfirm,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Confirm or override the client name. Also updates linked products."""
    ingestion = db.query(EmailIngestion).filter(EmailIngestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Email ingestion not found")

    ingestion.confirmed_client = body.client_name

    if ingestion.status == EmailIngestionStatus.review:
        ingestion.status = EmailIngestionStatus.completed

    # Update linked products
    for att in ingestion.attachments:
        if att.job_id:
            job = db.query(CoAJob).filter(CoAJob.id == att.job_id).first()
            if job and job.product_id:
                product = db.query(Product).filter(Product.id == job.product_id).first()
                if product:
                    product.client_name = body.client_name

    db.commit()
    db.refresh(ingestion)
    return ingestion


# ── Reclassify attachment ────────────────────────────────────────


@router.patch("/api/email/attachments/{attachment_id}/reclassify", response_model=EmailAttachmentResponse)
async def reclassify_attachment(
    attachment_id: str,
    body: EmailAttachmentReclassify,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Change an attachment's type. Triggers or cancels CoA processing as needed."""
    att = db.query(EmailAttachment).filter(EmailAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")

    old_type = att.attachment_type
    new_type = body.attachment_type
    att.attachment_type = new_type

    ingestion = db.query(EmailIngestion).filter(EmailIngestion.id == att.email_ingestion_id).first()
    source_path = settings.email_attachments_path / att.email_ingestion_id / att.stored_filename

    # If changing FROM coa → product_photo, no new job needed (existing job stays)
    # If changing TO coa_pdf/coa_photo FROM product_photo, create a new CoA job
    if old_type == AttachmentType.product_photo and new_type in (AttachmentType.coa_pdf, AttachmentType.coa_photo):
        if not att.job_id and source_path.exists():
            # Convert photo to PDF if needed
            if new_type == AttachmentType.coa_photo:
                from pathlib import Path as P
                pdf_name = f"{P(att.stored_filename).stem}.pdf"
                pdf_path = settings.uploads_path / pdf_name
                image_to_pdf(source_path, pdf_path)
                upload_filename = pdf_name
            else:
                upload_filename = att.stored_filename
                dest = settings.uploads_path / upload_filename
                dest.write_bytes(source_path.read_bytes())

            job = CoAJob(
                filename=upload_filename,
                status=JobStatus.queued,
                email_ingestion_id=att.email_ingestion_id,
            )
            db.add(job)
            db.flush()
            att.job_id = job.id

            thread = threading.Thread(target=process_coa, args=(job.id,), daemon=True)
            thread.start()

    db.commit()
    db.refresh(att)
    return att


# ── Serve attachment file ────────────────────────────────────────


@router.get("/api/email/attachments/{attachment_id}/file")
async def get_attachment_file(
    attachment_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Serve the raw attachment file."""
    att = db.query(EmailAttachment).filter(EmailAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = settings.email_attachments_path / att.email_ingestion_id / att.stored_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(path=str(file_path), filename=att.original_filename)


# ── Manual poll trigger ──────────────────────────────────────────


@router.post("/api/email/poll")
async def manual_poll(
    _admin: str = Depends(get_admin_user),
):
    """Manually trigger an inbox poll."""
    count = poll_inbox_once()
    return {"polled": True, "new_emails": count}


# ── List product photos ─────────────────────────────────────────


@router.get("/api/email/photos/{ingestion_id}", response_model=list[EmailAttachmentResponse])
async def list_product_photos(
    ingestion_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """List product-photo attachments for an email ingestion."""
    ingestion = db.query(EmailIngestion).filter(EmailIngestion.id == ingestion_id).first()
    if not ingestion:
        raise HTTPException(status_code=404, detail="Email ingestion not found")

    photos = (
        db.query(EmailAttachment)
        .filter(
            EmailAttachment.email_ingestion_id == ingestion_id,
            EmailAttachment.attachment_type == AttachmentType.product_photo,
        )
        .all()
    )
    return photos
