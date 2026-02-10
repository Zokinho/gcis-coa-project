"""Evernote router — preview and push product data to client Evernote notes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_admin_user
from backend.config import settings
from backend.database import get_db
from backend.models import (
    CoAJob,
    EvernotePushRequest,
    JobStatus,
    Product,
    ProductTestData,
)
from backend.services.evernote_service import preview_evernote_push, push_to_evernote

logger = logging.getLogger(__name__)
router = APIRouter(tags=["evernote"])


# ── Helpers ──────────────────────────────────────────────────────


def _load_job_product(job_id: str, db: Session):
    """Load job, product, and test data for Evernote push."""
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.published:
        raise HTTPException(status_code=400, detail="Job must be published first")
    if not job.product_id:
        raise HTTPException(status_code=400, detail="Job has no linked product")

    product = db.query(Product).filter(Product.id == job.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    test_data = db.query(ProductTestData).filter(ProductTestData.product_id == product.id).all()
    return job, product, test_data


# ── Routes ───────────────────────────────────────────────────────


@router.get("/api/evernote/preview/{job_id}")
async def evernote_preview(
    job_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Preview the Evernote note content that will be created/appended."""
    _job, product, test_data = _load_job_product(job_id, db)

    client_name = product.client_name
    if not client_name:
        raise HTTPException(
            status_code=400,
            detail="Product has no client_name set. Confirm client name first.",
        )

    try:
        return preview_evernote_push(product, test_data, client_name)
    except Exception as exc:
        logger.exception("Evernote preview failed")
        raise HTTPException(status_code=502, detail=f"Evernote error: {exc}")


@router.post("/api/evernote/push")
async def evernote_push(
    body: EvernotePushRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Push product data to the client's Evernote note (create or append)."""
    _job, product, test_data = _load_job_product(body.job_id, db)

    # Allow override via request body, fall back to product.client_name
    client_name = body.client_name or product.client_name
    if not client_name:
        raise HTTPException(
            status_code=400,
            detail="No client name provided. Set product.client_name or pass client_name in request.",
        )

    try:
        result = push_to_evernote(product, test_data, client_name)
        return result
    except Exception as exc:
        logger.exception("Evernote push failed")
        raise HTTPException(status_code=502, detail=f"Evernote error: {exc}")
