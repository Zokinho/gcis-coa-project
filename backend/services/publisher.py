"""Publisher — saves final product record and clean PDF to the published directory."""

import logging
from datetime import date, datetime
from pathlib import Path
import shutil

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import (
    CoAJob, ExtractionResult, JobStatus, Product, ProductGroup, ProductStatus, ProductTestData,
)
from backend.services.merger import TEST_SECTIONS
from backend.utils import normalize_product_name

logger = logging.getLogger(__name__)


def find_or_create_product_group(
    db: Session,
    name: str,
    client_name: str | None,
    merged: ExtractionResult,
    tags: list[str],
) -> ProductGroup:
    """Find an existing ProductGroup by normalized name + client, or create a new one."""
    norm = normalize_product_name(name)

    # Query for existing group
    query = db.query(ProductGroup).filter(ProductGroup.normalized_name == norm)
    if client_name:
        query = query.filter(ProductGroup.client_name == client_name)
    else:
        query = query.filter(ProductGroup.client_name.is_(None))

    group = query.first()

    if group:
        logger.info("Matched existing ProductGroup '%s' (id=%s)", group.name, group.id)
        # Mark all existing products in this group as not-latest
        db.query(Product).filter(
            Product.product_group_id == group.id,
            Product.is_latest == True,
        ).update({"is_latest": False})
        # Refresh group metadata
        group.updated_at = datetime.utcnow()
        if tags:
            group.tags = tags
        return group

    # Build search text
    search_parts = [name, merged.lot_number or "", merged.lab or "",
                    merged.producer or "", merged.strain_type or ""]
    search_text = " ".join(p for p in search_parts if p).lower()

    group = ProductGroup(
        name=name,
        normalized_name=norm,
        strain_type=merged.strain_type,
        producer=merged.producer,
        client_name=client_name,
        tier="gacp-small",
        status=ProductStatus.review,
        available=True,
        tags=tags,
        search_text=search_text,
    )
    db.add(group)
    db.flush()
    logger.info("Created new ProductGroup '%s' (id=%s)", group.name, group.id)
    return group


def publish_product(
    db: Session,
    job: CoAJob,
    merged: ExtractionResult,
    tags: list[str],
    redacted_pdf_path: Path,
) -> Product:
    """Create or update a Product record from the merged extraction, and copy the clean PDF."""

    # Parse test_date
    test_date = None
    if merged.test_date:
        try:
            test_date = date.fromisoformat(merged.test_date)
        except (ValueError, TypeError):
            logger.warning("Could not parse test_date: %s", merged.test_date)

    # Build search text for full-text search
    search_parts = [
        merged.product_name or "",
        merged.lot_number or "",
        merged.lab or "",
        merged.producer or "",
        merged.strain_type or "",
        merged.report_number or "",
    ]
    search_text = " ".join(p for p in search_parts if p).lower()

    product = Product(
        name=merged.product_name or "Unknown Product",
        strain_type=merged.strain_type,
        lot_number=merged.lot_number or "N/A",
        producer=merged.producer,
        lab=merged.lab or "Unknown Lab",
        test_date=test_date,
        report_number=merged.report_number,
        tier="gacp-small",  # Default tier, GCIS assigns during review
        status=ProductStatus.review,
        available=True,
        tags=tags,
        search_text=search_text,
    )
    db.add(product)
    db.flush()  # Get the product.id

    # Save test data sections
    for section_name in TEST_SECTIONS:
        section_data = getattr(merged, section_name, None)
        if section_data:
            test_record = ProductTestData(
                product_id=product.id,
                test_type=section_name,
                data=section_data,
                lab=merged.lab or "Unknown",
                test_date=test_date,
            )
            db.add(test_record)

    # Link job to product
    job.product_id = product.id
    job.status = JobStatus.review

    # Auto-match to ProductGroup
    product_name = merged.product_name or "Unknown Product"
    client_name = job.client_name  # May be None
    group = find_or_create_product_group(db, product_name, client_name, merged, tags)
    product.product_group_id = group.id
    product.is_latest = True
    product.client_name = client_name

    # Copy redacted PDF to published directory
    pub_dir = settings.published_path / product.id
    pub_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (merged.product_name or "product").replace(" ", "_").replace("/", "_")
    safe_lot = (merged.lot_number or "unknown").replace(" ", "_").replace("/", "_")
    dest = pub_dir / f"{safe_name}_{safe_lot}_CoA.pdf"
    shutil.copy2(redacted_pdf_path, dest)

    db.commit()

    logger.info("Published product %s (id=%s, group=%s) from job %s",
                product.name, product.id, group.id, job.id)
    return product
