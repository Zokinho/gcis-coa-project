"""Product groups router — group multiple CoAs under a single strain/SKU."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.auth import get_admin_user
from backend.config import settings
from backend.database import get_db
from backend.models import (
    AccessToken,
    CoAHistoryItem,
    Product,
    ProductGroup,
    ProductGroupCreate,
    ProductGroupDetailResponse,
    ProductGroupResponse,
    ProductGroupUpdate,
    ProductResponse,
    ProductStatus,
    ProductTestDataResponse,
)
from backend.utils import normalize_product_name

logger = logging.getLogger(__name__)
router = APIRouter(tags=["product-groups"])


# ── Helpers ─────────────────────────────────────────────────────


def _validate_buyer_token(token: str | None, db: Session) -> list[str] | None:
    if not token:
        return None
    access_token = db.query(AccessToken).filter(
        AccessToken.token == token,
        AccessToken.active == True,
    ).first()
    if not access_token:
        raise HTTPException(status_code=403, detail="Invalid or inactive access token")
    return access_token.tiers


def _build_group_response(group: ProductGroup, db: Session) -> ProductGroupResponse:
    """Build a ProductGroupResponse with coa_count and latest_product."""
    products = (
        db.query(Product)
        .filter(Product.product_group_id == group.id)
        .order_by(Product.created_at.desc())
        .all()
    )
    latest = next((p for p in products if p.is_latest), products[0] if products else None)

    return ProductGroupResponse(
        id=group.id,
        name=group.name,
        strain_type=group.strain_type,
        producer=group.producer,
        client_name=group.client_name,
        tier=group.tier,
        status=group.status,
        available=group.available,
        tags=group.tags or [],
        created_at=group.created_at,
        updated_at=group.updated_at,
        coa_count=len(products),
        latest_product=ProductResponse.model_validate(latest) if latest else None,
    )


def _build_group_detail(group: ProductGroup, db: Session) -> ProductGroupDetailResponse:
    """Build a detailed group response with full product list and CoA history."""
    products = (
        db.query(Product)
        .filter(Product.product_group_id == group.id)
        .order_by(Product.created_at.desc())
        .all()
    )
    latest = next((p for p in products if p.is_latest), products[0] if products else None)

    history = [
        CoAHistoryItem(
            product_id=p.id,
            lot_number=p.lot_number,
            lab=p.lab,
            test_date=p.test_date,
            report_number=p.report_number,
            is_latest=p.is_latest,
            created_at=p.created_at,
        )
        for p in products
    ]

    return ProductGroupDetailResponse(
        id=group.id,
        name=group.name,
        strain_type=group.strain_type,
        producer=group.producer,
        client_name=group.client_name,
        tier=group.tier,
        status=group.status,
        available=group.available,
        tags=group.tags or [],
        created_at=group.created_at,
        updated_at=group.updated_at,
        coa_count=len(products),
        latest_product=ProductResponse.model_validate(latest) if latest else None,
        products=[ProductResponse.model_validate(p) for p in products],
        coa_history=history,
    )


# ── Buyer endpoints (public, token-validated) ───────────────────


@router.get("/api/product-groups", response_model=list[ProductGroupResponse])
def list_product_groups(
    q: str | None = None,
    tier: str | None = None,
    tag: str | None = None,
    token: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List published product groups with latest product data."""
    allowed_tiers = _validate_buyer_token(token, db)

    query = db.query(ProductGroup).filter(ProductGroup.status == ProductStatus.published)

    if allowed_tiers:
        query = query.filter(ProductGroup.tier.in_(allowed_tiers))

    if q:
        query = query.filter(ProductGroup.search_text.contains(q.lower()))

    if tier:
        query = query.filter(ProductGroup.tier == tier)

    if tag:
        query = query.filter(ProductGroup.tags.contains(tag))

    groups = (
        query.order_by(ProductGroup.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return [_build_group_response(g, db) for g in groups]


@router.get("/api/product-groups/{group_id}", response_model=ProductGroupDetailResponse)
def get_product_group(
    group_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Get group detail with latest test data + CoA history."""
    allowed_tiers = _validate_buyer_token(token, db)

    group = db.query(ProductGroup).filter(ProductGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Product group not found")

    if group.status != ProductStatus.published:
        raise HTTPException(status_code=404, detail="Product group not found")

    if allowed_tiers and group.tier not in allowed_tiers:
        raise HTTPException(status_code=403, detail="Access denied for this product tier")

    return _build_group_detail(group, db)


@router.get("/api/product-groups/{group_id}/coas/{product_id}/pdf")
def get_group_coa_pdf(
    group_id: str,
    product_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Download a specific CoA's PDF from a product group."""
    _validate_buyer_token(token, db)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.product_group_id == group_id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in this group")

    pub_dir = settings.published_path / product.id
    pdfs = list(pub_dir.glob("*.pdf")) if pub_dir.exists() else []
    if not pdfs:
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=pdfs[0],
        media_type="application/pdf",
        filename=pdfs[0].name,
    )


# ── Admin endpoints ─────────────────────────────────────────────


@router.get("/api/admin/product-groups", response_model=list[ProductGroupResponse])
def admin_list_product_groups(
    q: str | None = None,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """List all product groups with coa_count."""
    query = db.query(ProductGroup)

    if q:
        query = query.filter(ProductGroup.search_text.contains(q.lower()))

    groups = query.order_by(ProductGroup.updated_at.desc()).all()
    return [_build_group_response(g, db) for g in groups]


@router.get("/api/admin/product-groups/{group_id}", response_model=ProductGroupDetailResponse)
def admin_get_product_group(
    group_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Get detailed group with all linked products."""
    group = db.query(ProductGroup).filter(ProductGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Product group not found")
    return _build_group_detail(group, db)


@router.patch("/api/admin/product-groups/{group_id}", response_model=ProductGroupResponse)
def admin_update_product_group(
    group_id: str,
    body: ProductGroupUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Update group fields (tier, name, tags, client_name, etc.)."""
    group = db.query(ProductGroup).filter(ProductGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Product group not found")

    if body.name is not None:
        group.name = body.name
        group.normalized_name = normalize_product_name(body.name)
    if body.strain_type is not None:
        group.strain_type = body.strain_type
    if body.producer is not None:
        group.producer = body.producer
    if body.client_name is not None:
        group.client_name = body.client_name
    if body.tier is not None:
        group.tier = body.tier
    if body.tags is not None:
        group.tags = body.tags
    if body.available is not None:
        group.available = body.available

    db.commit()
    db.refresh(group)
    return _build_group_response(group, db)


@router.post("/api/admin/product-groups/{group_id}/reassign")
def admin_reassign_product(
    group_id: str,
    product_id: str = Query(..., description="The product ID to reassign"),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Move a product (CoA) into this group."""
    group = db.query(ProductGroup).filter(ProductGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Product group not found")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    old_group_id = product.product_group_id
    product.product_group_id = group.id
    product.is_latest = False  # Admin should explicitly set latest after reassign

    # If old group now has no latest, promote the newest
    if old_group_id and old_group_id != group_id:
        remaining = (
            db.query(Product)
            .filter(Product.product_group_id == old_group_id)
            .order_by(Product.created_at.desc())
            .all()
        )
        if remaining and not any(p.is_latest for p in remaining):
            remaining[0].is_latest = True

    db.commit()
    return {"ok": True, "product_id": product_id, "group_id": group_id}


@router.post("/api/admin/product-groups/{group_id}/set-latest")
def admin_set_latest_coa(
    group_id: str,
    product_id: str = Query(..., description="The product ID to mark as latest"),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Manually set which CoA is the latest for this group."""
    group = db.query(ProductGroup).filter(ProductGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Product group not found")

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.product_group_id == group_id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in this group")

    # Clear existing latest
    db.query(Product).filter(
        Product.product_group_id == group_id,
        Product.is_latest == True,
    ).update({"is_latest": False})

    product.is_latest = True
    db.commit()
    return {"ok": True, "product_id": product_id, "group_id": group_id}
