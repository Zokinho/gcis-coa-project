"""Products router — public product catalog for buyers."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import (
    AccessToken,
    CoAJob,
    PdfInfoResponse,
    Product,
    ProductDetailResponse,
    ProductResponse,
    ProductStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/products", tags=["products"])


def _validate_buyer_token(token: str | None, db: Session) -> list[str] | None:
    """Validate buyer token and return allowed tiers. Returns None if no token."""
    if not token:
        return None
    access_token = db.query(AccessToken).filter(
        AccessToken.token == token,
        AccessToken.active == True,
    ).first()
    if not access_token:
        raise HTTPException(status_code=403, detail="Invalid or inactive access token")
    return access_token.tiers


@router.get("", response_model=list[ProductResponse])
def list_products(
    q: str | None = None,
    tier: str | None = None,
    tag: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """List published products. Optionally filter by buyer token tiers."""
    allowed_tiers = _validate_buyer_token(token, db)

    query = db.query(Product).filter(Product.status == ProductStatus.published)

    if allowed_tiers:
        query = query.filter(Product.tier.in_(allowed_tiers))

    if q:
        query = query.filter(Product.search_text.contains(q.lower()))

    if tier:
        query = query.filter(Product.tier == tier)

    if tag:
        query = query.filter(Product.tags.contains(tag))

    total = query.count()
    products = (
        query.order_by(Product.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return products


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(
    product_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Get full product detail with test data."""
    allowed_tiers = _validate_buyer_token(token, db)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status != ProductStatus.published:
        raise HTTPException(status_code=404, detail="Product not found")

    if allowed_tiers and product.tier not in allowed_tiers:
        raise HTTPException(status_code=403, detail="Access denied for this product tier")

    return product


@router.get("/{product_id}/pdf")
def get_product_pdf(
    product_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Stream the published/redacted PDF for a product."""
    allowed_tiers = _validate_buyer_token(token, db)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status != ProductStatus.published:
        raise HTTPException(status_code=404, detail="Product not found")

    if allowed_tiers and product.tier not in allowed_tiers:
        raise HTTPException(status_code=403, detail="Access denied for this product tier")

    pub_dir = settings.published_path / product.id
    if not pub_dir.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    pdf_files = list(pub_dir.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        pdf_files[0],
        media_type="application/pdf",
        filename=pdf_files[0].name,
    )


@router.get("/{product_id}/pdf-info", response_model=PdfInfoResponse)
def get_product_pdf_info(
    product_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Return PDF metadata (filename, file_size, page_count) without downloading."""
    allowed_tiers = _validate_buyer_token(token, db)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status != ProductStatus.published:
        raise HTTPException(status_code=404, detail="Product not found")

    if allowed_tiers and product.tier not in allowed_tiers:
        raise HTTPException(status_code=403, detail="Access denied for this product tier")

    pub_dir = settings.published_path / product.id
    if not pub_dir.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    pdf_files = list(pub_dir.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="PDF not found")

    pdf_path = pdf_files[0]
    file_size = os.path.getsize(pdf_path)

    # Get page count from CoA job
    page_count = 0
    job = db.query(CoAJob).filter(CoAJob.product_id == product_id).first()
    if job:
        page_count = job.page_count

    return PdfInfoResponse(
        filename=pdf_path.name,
        file_size=file_size,
        page_count=page_count,
    )
