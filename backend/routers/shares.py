"""Curated shares router — admin creates shareable product selections."""

import logging
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.auth import get_admin_user
from backend.config import settings
from backend.database import get_db
from backend.models import (
    CuratedShare,
    CuratedShareCreate,
    CuratedShareResponse,
    CuratedShareUpdate,
    Product,
    ProductDetailResponse,
    ProductGroup,
    ProductStatus,
    ProductTestData,
    ProductTestDataResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["shares"])


# ── Admin endpoints ──────────────────────────────────────────────


@router.post("/api/shares", response_model=CuratedShareResponse)
async def create_share(
    body: CuratedShareCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Create a curated share with a unique token."""
    share = CuratedShare(
        token=secrets.token_urlsafe(32),
        label=body.label,
        product_ids=body.product_ids,
        product_group_ids=body.product_group_ids,
        expires_at=body.expires_at,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


@router.get("/api/shares", response_model=list[CuratedShareResponse])
async def list_shares(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """List all curated shares."""
    shares = db.query(CuratedShare).order_by(CuratedShare.created_at.desc()).all()
    return shares


@router.patch("/api/shares/{share_id}", response_model=CuratedShareResponse)
async def update_share(
    share_id: str,
    body: CuratedShareUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Update a curated share."""
    share = db.query(CuratedShare).filter(CuratedShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    if body.label is not None:
        share.label = body.label
    if body.product_ids is not None:
        share.product_ids = body.product_ids
    if body.product_group_ids is not None:
        share.product_group_ids = body.product_group_ids
    if body.active is not None:
        share.active = body.active
    if body.expires_at is not None:
        share.expires_at = body.expires_at

    db.commit()
    db.refresh(share)
    return share


@router.delete("/api/shares/{share_id}")
async def delete_share(
    share_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Deactivate a curated share."""
    share = db.query(CuratedShare).filter(CuratedShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    share.active = False
    db.commit()
    return {"ok": True}


# ── Public endpoints ─────────────────────────────────────────────


def _validate_share(token: str, db: Session) -> CuratedShare:
    """Validate a share token (active + not expired). Returns the share or raises."""
    share = db.query(CuratedShare).filter(CuratedShare.token == token).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    if not share.active:
        raise HTTPException(status_code=410, detail="This share link has been deactivated")
    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This share link has expired")
    return share


@router.get("/api/shares/validate/{token}")
async def validate_share(
    token: str,
    db: Session = Depends(get_db),
):
    """Validate a curated share token (public). Returns label + product count."""
    share = _validate_share(token, db)

    # Increment usage
    share.use_count += 1
    share.last_used = datetime.utcnow()
    db.commit()

    return {
        "valid": True,
        "label": share.label,
        "product_count": len(share.product_ids),
        "product_group_count": len(share.product_group_ids or []),
    }


@router.get("/api/shares/{token}/products", response_model=list[ProductDetailResponse])
async def get_share_products(
    token: str,
    db: Session = Depends(get_db),
):
    """Get products in a curated share (public).

    If product_group_ids is populated, resolve to latest product per group.
    Falls back to product_ids for backward compatibility.
    """
    share = _validate_share(token, db)

    product_list: list[Product] = []

    # Resolve product_group_ids to latest products
    if share.product_group_ids:
        for gid in share.product_group_ids:
            latest = (
                db.query(Product)
                .filter(
                    Product.product_group_id == gid,
                    Product.is_latest == True,
                    Product.status == ProductStatus.published,
                )
                .first()
            )
            if latest:
                product_list.append(latest)

    # Also include any direct product_ids (backward compat)
    if share.product_ids:
        already = {p.id for p in product_list}
        direct = (
            db.query(Product)
            .filter(
                Product.id.in_(share.product_ids),
                Product.status == ProductStatus.published,
            )
            .all()
        )
        for p in direct:
            if p.id not in already:
                product_list.append(p)

    result = []
    for p in product_list:
        test_data = db.query(ProductTestData).filter(ProductTestData.product_id == p.id).all()
        result.append(
            ProductDetailResponse(
                id=p.id,
                name=p.name,
                strain_type=p.strain_type,
                lot_number=p.lot_number,
                producer=p.producer,
                lab=p.lab,
                test_date=p.test_date,
                report_number=p.report_number,
                tier=p.tier,
                status=p.status,
                available=p.available,
                tags=p.tags or [],
                client_name=p.client_name,
                created_at=p.created_at,
                product_group_id=p.product_group_id,
                is_latest=p.is_latest,
                test_data=[ProductTestDataResponse.model_validate(td) for td in test_data],
            )
        )
    return result


@router.get("/api/shares/{token}/products/{product_id}/pdf")
async def get_share_product_pdf(
    token: str,
    product_id: str,
    db: Session = Depends(get_db),
):
    """Serve PDF for a product in a curated share (public)."""
    share = _validate_share(token, db)

    # Check direct product_ids OR product belongs to a shared group
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.status != ProductStatus.published:
        raise HTTPException(status_code=404, detail="Product not found")
    in_direct = product_id in (share.product_ids or [])
    in_group = product.product_group_id and product.product_group_id in (share.product_group_ids or [])
    if not in_direct and not in_group:
        raise HTTPException(status_code=403, detail="Product not in this share")

    pub_dir = settings.published_path / product.id
    pdfs = list(pub_dir.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=pdfs[0],
        media_type="application/pdf",
        filename=pdfs[0].name,
    )
