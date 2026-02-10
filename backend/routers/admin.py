"""Admin router — login, stats, job management."""

import logging
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth import create_access_token, get_admin_user, verify_credentials
from backend.config import settings
from backend.database import get_db
from backend.models import (
    AdminLogin,
    ClientProductResponse,
    ClientSummary,
    CoAJob,
    DashboardStats,
    JobResponse,
    JobStatus,
    Product,
    ProductDetailResponse,
    ProductGroup,
    ProductPhoto,
    ProductPhotoResponse,
    ProductStatus,
    ProductUpdate,
    RedactionRegion,
    SyncLog,
    SyncLogResponse,
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
    if body.product_group_id is not None:
        # Verify group exists
        group = db.query(ProductGroup).filter(ProductGroup.id == body.product_group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Product group not found")
        product.product_group_id = body.product_group_id

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
    group_count = db.query(ProductGroup).count()

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
        total_product_groups=group_count,
    )


# ── Client Records ────────────────────────────────────────────────


def _get_pdf_metadata(product: Product) -> tuple[str | None, int, int]:
    """Return (filename, file_size, page_count) for a product's published PDF."""
    pub_dir = settings.published_path / product.id
    if not pub_dir.exists():
        return None, 0, 0
    pdf_files = list(pub_dir.glob("*.pdf"))
    if not pdf_files:
        return None, 0, 0
    pdf_path = pdf_files[0]
    file_size = os.path.getsize(pdf_path)
    # Get page count from the CoA job
    page_count = 0
    if product.job:
        page_count = product.job.page_count
    return pdf_path.name, file_size, page_count


@router.get("/api/admin/clients", response_model=list[ClientSummary])
def list_clients(
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """List unique clients with product counts."""
    query = (
        db.query(
            Product.client_name,
            func.count(Product.id).label("product_count"),
            func.max(Product.test_date).label("latest_test_date"),
        )
        .filter(Product.client_name.isnot(None), Product.client_name != "")
        .group_by(Product.client_name)
    )

    if q:
        query = query.filter(Product.client_name.ilike(f"%{q}%"))

    rows = query.order_by(Product.client_name).all()

    result = []
    for client_name, product_count, latest_test_date in rows:
        # Get distinct tiers for this client
        tiers = (
            db.query(Product.tier)
            .filter(Product.client_name == client_name)
            .distinct()
            .all()
        )
        result.append(
            ClientSummary(
                client_name=client_name,
                product_count=product_count,
                latest_test_date=latest_test_date,
                tiers=[t[0] for t in tiers],
            )
        )
    return result


@router.get("/api/admin/clients/{client_name}/products", response_model=list[ClientProductResponse])
def list_client_products(
    client_name: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """List products for a specific client with PDF metadata."""
    products = (
        db.query(Product)
        .filter(Product.client_name == client_name)
        .order_by(Product.test_date.desc().nullslast(), Product.created_at.desc())
        .all()
    )

    result = []
    for p in products:
        pdf_filename, pdf_file_size, pdf_page_count = _get_pdf_metadata(p)

        syncs = db.query(SyncLog).filter(SyncLog.product_id == p.id).all()
        photos = db.query(ProductPhoto).filter(ProductPhoto.product_id == p.id).all()

        group_name = None
        if p.product_group_id and p.product_group:
            group_name = p.product_group.name

        result.append(
            ClientProductResponse(
                id=p.id,
                name=p.name,
                strain_type=p.strain_type,
                lot_number=p.lot_number,
                lab=p.lab,
                test_date=p.test_date,
                tier=p.tier,
                status=p.status,
                pdf_filename=pdf_filename,
                pdf_page_count=pdf_page_count,
                pdf_file_size=pdf_file_size,
                job_id=p.job.id if p.job else None,
                syncs=[SyncLogResponse.model_validate(s) for s in syncs],
                photos=[ProductPhotoResponse.model_validate(ph) for ph in photos],
                product_group_id=p.product_group_id,
                product_group_name=group_name,
            )
        )
    return result


@router.get("/api/admin/products/{product_id}/photos/{photo_id}")
def serve_product_photo(
    product_id: str,
    photo_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Serve a product photo file."""
    photo = (
        db.query(ProductPhoto)
        .filter(ProductPhoto.id == photo_id, ProductPhoto.product_id == product_id)
        .first()
    )
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo_path = Path(photo.stored_filename)
    if not photo_path.exists():
        raise HTTPException(status_code=404, detail="Photo file not found on disk")

    return FileResponse(
        path=photo_path,
        media_type=photo.mime_type,
        filename=photo.original_filename,
    )
