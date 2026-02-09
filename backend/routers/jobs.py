"""Jobs router — check job status, manage redactions, publish."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import (
    CoAJob, JobResponse, JobStatus, Product, ProductResponse,
    RedactionRegion, RedactionRegionResponse, RedactionToggle,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    """List all CoA processing jobs."""
    jobs = db.query(CoAJob).order_by(CoAJob.created_at.desc()).all()
    return jobs


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get status and details of a specific job."""
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/redactions", response_model=list[RedactionRegionResponse])
def get_redactions(job_id: str, db: Session = Depends(get_db)):
    """Get all redaction regions for a job."""
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    regions = (
        db.query(RedactionRegion)
        .filter(RedactionRegion.job_id == job_id)
        .order_by(RedactionRegion.page, RedactionRegion.y_pct)
        .all()
    )
    return regions


@router.patch("/jobs/{job_id}/redactions/{redaction_id}", response_model=RedactionRegionResponse)
def toggle_redaction(
    job_id: str,
    redaction_id: str,
    body: RedactionToggle,
    db: Session = Depends(get_db),
):
    """Toggle a redaction region on or off."""
    region = (
        db.query(RedactionRegion)
        .filter(RedactionRegion.id == redaction_id, RedactionRegion.job_id == job_id)
        .first()
    )
    if not region:
        raise HTTPException(status_code=404, detail="Redaction region not found")

    if body.approved is not None:
        region.approved = body.approved
    if body.x_pct is not None:
        region.x_pct = body.x_pct
    if body.y_pct is not None:
        region.y_pct = body.y_pct
    if body.w_pct is not None:
        region.w_pct = body.w_pct
    if body.h_pct is not None:
        region.h_pct = body.h_pct
    db.commit()
    db.refresh(region)
    return region


@router.get("/jobs/{job_id}/pages/{page_num}")
def get_page_image(job_id: str, page_num: int, db: Session = Depends(get_db)):
    """Serve a page image for the review UI."""
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    image_path = settings.working_path / job.id / f"page_{page_num}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Page image not found")
    return FileResponse(image_path, media_type="image/png")


@router.get("/jobs/{job_id}/product", response_model=ProductResponse)
def get_job_product(job_id: str, db: Session = Depends(get_db)):
    """Get the extracted product for a job."""
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.product_id:
        raise HTTPException(status_code=404, detail="No product extracted yet")

    product = db.query(Product).filter(Product.id == job.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
