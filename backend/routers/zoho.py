"""Zoho CRM router — preview field mapping and push products."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_admin_user
from backend.config import settings
from backend.database import get_db
from backend.models import CoAJob, JobStatus, Product, ProductTestData
from backend.services.zoho_crm import build_field_mapping, push_product_with_pdf

logger = logging.getLogger(__name__)
router = APIRouter(tags=["zoho"])


class ZohoPushRequest(BaseModel):
    job_id: str


# ── Helpers ──────────────────────────────────────────────────────


def _load_job_product_pdf(job_id: str, db: Session):
    """Shared validation: load job, product, test data, and PDF path."""
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.published:
        raise HTTPException(status_code=400, detail="Job must be published before pushing to Zoho CRM")
    if not job.product_id:
        raise HTTPException(status_code=400, detail="Job has no linked product")

    product = db.query(Product).filter(Product.id == job.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    test_data = db.query(ProductTestData).filter(ProductTestData.product_id == product.id).all()

    pub_dir = settings.published_path / product.id
    pdfs = list(pub_dir.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(status_code=404, detail="Published PDF not found on disk")

    return job, product, test_data, pdfs[0]


# ── Routes ───────────────────────────────────────────────────────


@router.get("/api/zoho/preview/{job_id}")
async def zoho_preview(
    job_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Return the Zoho CRM field mapping without making any API call."""
    _job, product, test_data, pdf_path = _load_job_product_pdf(job_id, db)
    fields = build_field_mapping(product, test_data)
    return {
        "fields": fields,
        "pdf_filename": pdf_path.name,
    }


@router.post("/api/zoho/push")
async def zoho_push(
    body: ZohoPushRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Create a Zoho CRM Product record and attach the published PDF."""
    _job, product, test_data, pdf_path = _load_job_product_pdf(body.job_id, db)

    try:
        result = await push_product_with_pdf(product, test_data, pdf_path)
        return result
    except Exception as exc:
        logger.exception("Zoho CRM push failed")
        raise HTTPException(status_code=502, detail=f"Zoho CRM error: {exc}")
