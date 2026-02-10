"""Admin router — login, stats, job management."""

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.auth import create_access_token, get_admin_user, verify_credentials
from backend.config import settings
from backend.database import get_db
from backend.models import (
    AdminLogin,
    CoAJob,
    DashboardStats,
    JobResponse,
    JobStatus,
    Product,
    ProductDetailResponse,
    ProductStatus,
    ProductUpdate,
    RedactionRegion,
    AccessToken,
)
from backend.tasks.dispatch import send_process_coa

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


# ── Auth endpoints ────────────────────────────────────────────────


@router.post("/api/auth/login")
def login(body: AdminLogin, response: Response):
    if not verify_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(body.username)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return {"ok": True, "username": body.username}


@router.get("/api/auth/me")
def me(username: str = Depends(get_admin_user)):
    return {"username": username}


@router.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie("session_token")
    return {"ok": True}


# ── Admin job management ──────────────────────────────────────────


@router.post("/api/admin/jobs/{job_id}/publish", response_model=JobResponse)
def publish_job(
    job_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.review, JobStatus.flagged):
        raise HTTPException(status_code=400, detail=f"Cannot publish job in '{job.status.value}' status")

    # Re-apply redactions with current approved/rejected state
    work_dir = settings.working_path / job.id
    page_images = sorted(work_dir.glob("page_*.png"))
    if not page_images:
        raise HTTPException(status_code=400, detail="Page images not found — cannot re-apply redactions")

    regions = (
        db.query(RedactionRegion)
        .filter(RedactionRegion.job_id == job_id)
        .all()
    )
    region_dicts = [
        {
            "page": r.page,
            "x_pct": r.x_pct,
            "y_pct": r.y_pct,
            "w_pct": r.w_pct,
            "h_pct": r.h_pct,
            "approved": r.approved,
            "reason": r.reason,
        }
        for r in regions
    ]

    from backend.services.redactor import apply_redactions

    redacted_dir = settings.redacted_path / job.id
    redacted_dir.mkdir(parents=True, exist_ok=True)
    redacted_pdf = redacted_dir / "preview.pdf"
    apply_redactions(page_images, region_dicts, redacted_pdf)

    # Copy new redacted PDF to published directory
    if job.product_id:
        product = db.query(Product).filter(Product.id == job.product_id).first()
        if product:
            product.status = ProductStatus.published
            pub_dir = settings.published_path / product.id
            pub_dir.mkdir(parents=True, exist_ok=True)
            # Replace existing PDF(s)
            for old_pdf in pub_dir.glob("*.pdf"):
                old_pdf.unlink()
            safe_name = product.name.replace(" ", "_").replace("/", "_")
            safe_lot = product.lot_number.replace(" ", "_").replace("/", "_")
            dest = pub_dir / f"{safe_name}_{safe_lot}_CoA.pdf"
            shutil.copy2(redacted_pdf, dest)

    job.status = JobStatus.published
    db.commit()
    db.refresh(job)
    return job


@router.post("/api/admin/jobs/{job_id}/rescan", response_model=JobResponse)
def rescan_job(
    job_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus.queued
    job.error_message = None
    db.commit()
    db.refresh(job)

    send_process_coa(job.id)
    return job


# ── Admin product management ──────────────────────────────────────


@router.patch("/api/admin/products/{product_id}", response_model=ProductDetailResponse)
def update_product(
    product_id: str,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if body.name is not None:
        product.name = body.name
    if body.tier is not None:
        product.tier = body.tier
    if body.tags is not None:
        product.tags = body.tags
    if body.available is not None:
        product.available = body.available

    db.commit()
    db.refresh(product)
    return product


# ── Dashboard stats ───────────────────────────────────────────────


@router.get("/api/admin/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    jobs = db.query(CoAJob).all()
    status_counts = {}
    for j in jobs:
        status_counts[j.status.value] = status_counts.get(j.status.value, 0) + 1

    products = db.query(Product).all()
    published_count = sum(1 for p in products if p.status == ProductStatus.published)
    token_count = db.query(AccessToken).count()

    return DashboardStats(
        total_jobs=len(jobs),
        queued=status_counts.get("queued", 0),
        processing=status_counts.get("processing", 0),
        review=status_counts.get("review", 0),
        published=status_counts.get("published", 0),
        flagged=status_counts.get("flagged", 0),
        error=status_counts.get("error", 0),
        total_products=len(products),
        products_published=published_count,
        total_tokens=token_count,
    )
