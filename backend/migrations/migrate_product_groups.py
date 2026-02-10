"""Idempotent migration: create product_groups table and link existing products.

Usage:
    python -m backend.migrations.migrate_product_groups
"""

import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text

# Add project root to path for standalone execution
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backend.database import engine, SessionLocal
from backend.models import Base, Product, ProductGroup, CuratedShare
from backend.utils import normalize_product_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def run_migration():
    inspector = inspect(engine)

    # Step 1: Create product_groups table if needed
    if not _table_exists(inspector, "product_groups"):
        logger.info("Creating product_groups table...")
        ProductGroup.__table__.create(engine)
        logger.info("product_groups table created.")
    else:
        logger.info("product_groups table already exists.")

    # Step 2: Add product_group_id and is_latest to products
    with engine.connect() as conn:
        if not _column_exists(inspector, "products", "product_group_id"):
            logger.info("Adding product_group_id column to products...")
            conn.execute(text("ALTER TABLE products ADD COLUMN product_group_id VARCHAR(36) REFERENCES product_groups(id)"))
            conn.commit()
            logger.info("product_group_id column added.")
        else:
            logger.info("products.product_group_id already exists.")

        if not _column_exists(inspector, "products", "is_latest"):
            logger.info("Adding is_latest column to products...")
            conn.execute(text("ALTER TABLE products ADD COLUMN is_latest BOOLEAN DEFAULT 0"))
            conn.commit()
            logger.info("is_latest column added.")
        else:
            logger.info("products.is_latest already exists.")

        # Step 3: Add product_group_ids to curated_shares
        if not _column_exists(inspector, "curated_shares", "product_group_ids"):
            logger.info("Adding product_group_ids column to curated_shares...")
            conn.execute(text("ALTER TABLE curated_shares ADD COLUMN product_group_ids JSON DEFAULT '[]'"))
            conn.commit()
            logger.info("product_group_ids column added.")
        else:
            logger.info("curated_shares.product_group_ids already exists.")

    # Step 4: Group existing products into ProductGroups
    db = SessionLocal()
    try:
        # Only process products that aren't already assigned to a group
        unlinked = db.query(Product).filter(Product.product_group_id.is_(None)).all()
        if not unlinked:
            logger.info("No unlinked products to migrate.")
        else:
            logger.info("Grouping %d unlinked products...", len(unlinked))

            # Group by normalized_name + client_name
            groups: dict[tuple[str, str | None], list[Product]] = defaultdict(list)
            for p in unlinked:
                key = (normalize_product_name(p.name), p.client_name)
                groups[key].append(p)

            for (norm_name, client_name), products in groups.items():
                # Check if a group already exists for this key
                existing = (
                    db.query(ProductGroup)
                    .filter(
                        ProductGroup.normalized_name == norm_name,
                        ProductGroup.client_name == client_name if client_name else ProductGroup.client_name.is_(None),
                    )
                    .first()
                )

                if existing:
                    group = existing
                    logger.info("Using existing group '%s' for %d products", group.name, len(products))
                else:
                    # Use the first product's metadata to seed the group
                    ref = products[0]
                    group = ProductGroup(
                        name=ref.name,
                        normalized_name=norm_name,
                        strain_type=ref.strain_type,
                        producer=ref.producer,
                        client_name=client_name,
                        tier=ref.tier,
                        status=ref.status,
                        available=ref.available,
                        tags=ref.tags or [],
                        search_text=ref.search_text,
                    )
                    db.add(group)
                    db.flush()
                    logger.info("Created group '%s' (id=%s) for %d products", group.name, group.id, len(products))

                # Link products and mark the newest as latest
                sorted_products = sorted(products, key=lambda p: p.created_at, reverse=True)
                for i, p in enumerate(sorted_products):
                    p.product_group_id = group.id
                    p.is_latest = (i == 0)

            db.commit()
            logger.info("Product grouping complete.")

        # Step 5: Backfill curated_shares.product_group_ids
        shares = db.query(CuratedShare).all()
        updated_shares = 0
        for share in shares:
            if share.product_group_ids:
                continue
            if not share.product_ids:
                continue
            # Find product_group_ids from linked products
            group_ids = set()
            for pid in share.product_ids:
                prod = db.query(Product).filter(Product.id == pid).first()
                if prod and prod.product_group_id:
                    group_ids.add(prod.product_group_id)
            if group_ids:
                share.product_group_ids = list(group_ids)
                updated_shares += 1
        if updated_shares:
            db.commit()
            logger.info("Backfilled product_group_ids for %d curated shares.", updated_shares)
        else:
            logger.info("No curated shares needed backfill.")

    finally:
        db.close()

    logger.info("Migration complete.")


if __name__ == "__main__":
    run_migration()
