"""Tests for ProductGroup architecture — normalize, publisher auto-matching, model integrity."""

import pytest
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from pathlib import Path

from backend.utils import normalize_product_name
from backend.models import (
    CoAJob,
    ExtractionResult,
    Product,
    ProductGroup,
    ProductStatus,
    ProductTestData,
    JobStatus,
    ProductGroupResponse,
    ProductGroupDetailResponse,
    CoAHistoryItem,
)


# ── normalize_product_name tests ───────────────────────────────


class TestNormalizeProductName:
    def test_basic_lowercase(self):
        assert normalize_product_name("Blue Pavé 7") == "blue pave 7"

    def test_accent_stripping(self):
        assert normalize_product_name("Crème Brûlée") == "creme brulee"

    def test_whitespace_collapse(self):
        assert normalize_product_name("  Blue   Pavé   7  ") == "blue pave 7"

    def test_empty_string(self):
        assert normalize_product_name("") == ""

    def test_none_handling(self):
        # The function expects a str but let's test empty
        assert normalize_product_name("") == ""

    def test_already_normalized(self):
        assert normalize_product_name("blue pave 7") == "blue pave 7"

    def test_unicode_normalization(self):
        # é as combining character vs precomposed
        name1 = "Pav\u00e9"  # precomposed
        name2 = "Pave\u0301"  # combining
        assert normalize_product_name(name1) == normalize_product_name(name2)

    def test_mixed_case(self):
        assert normalize_product_name("BLUE PAVÉ 7") == "blue pave 7"


# ── Publisher auto-matching tests ──────────────────────────────


class TestPublisherAutoMatch:
    """Test find_or_create_product_group logic."""

    def _make_db(self):
        """Create a mock DB session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        return db

    def test_creates_new_group_when_none_exists(self):
        from backend.services.publisher import find_or_create_product_group

        db = self._make_db()
        # No existing group found
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = None

        merged = ExtractionResult(
            product_name="Blue Pavé 7",
            strain_type="Hybrid",
            lot_number="LOT-001",
            lab="Eurofins",
        )

        group = find_or_create_product_group(db, "Blue Pavé 7", "Client A", merged, ["tag1"])

        assert group.name == "Blue Pavé 7"
        assert group.normalized_name == "blue pave 7"
        assert group.client_name == "Client A"
        assert group.strain_type == "Hybrid"
        db.add.assert_called_once()

    def test_matches_existing_group(self):
        from backend.services.publisher import find_or_create_product_group

        db = self._make_db()

        existing_group = ProductGroup(
            id="group-1",
            name="Blue Pavé 7",
            normalized_name="blue pave 7",
            client_name="Client A",
            strain_type="Hybrid",
        )
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = existing_group

        merged = ExtractionResult(
            product_name="Blue Pavé 7",
            lot_number="LOT-002",
            lab="Eurofins",
        )

        group = find_or_create_product_group(db, "Blue Pavé 7", "Client A", merged, [])

        assert group.id == "group-1"
        assert group.name == "Blue Pavé 7"
        # Should NOT have called db.add for a new group
        db.add.assert_not_called()

    def test_accent_insensitive_matching(self):
        """Blue Pave 7 should match Blue Pavé 7."""
        norm1 = normalize_product_name("Blue Pave 7")
        norm2 = normalize_product_name("Blue Pavé 7")
        assert norm1 == norm2


# ── Schema validation tests ─────────────────────────────────────


class TestProductGroupSchemas:
    def test_product_group_response(self):
        resp = ProductGroupResponse(
            id="g1",
            name="Blue Pavé 7",
            tier="gacp-small",
            status=ProductStatus.draft,
            available=True,
            tags=["sativa"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            coa_count=3,
        )
        assert resp.coa_count == 3
        assert resp.latest_product is None

    def test_coa_history_item(self):
        item = CoAHistoryItem(
            product_id="p1",
            lot_number="LOT-001",
            lab="Eurofins",
            test_date=date(2024, 3, 15),
            report_number="RPT-001",
            is_latest=True,
            created_at=datetime.utcnow(),
        )
        assert item.is_latest is True
        assert item.lot_number == "LOT-001"

    def test_product_group_detail_response(self):
        resp = ProductGroupDetailResponse(
            id="g1",
            name="Blue Pavé 7",
            tier="gacp-small",
            status=ProductStatus.published,
            available=True,
            tags=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            coa_count=2,
            products=[],
            coa_history=[],
        )
        assert resp.products == []
        assert resp.coa_history == []


# ── Migration idempotency test ──────────────────────────────────


class TestMigrationHelpers:
    def test_normalize_used_for_grouping(self):
        """Products with same normalized name should end up in the same group."""
        names = ["Blue Pavé 7", "BLUE PAVE 7", "blue pavé  7"]
        normalized = [normalize_product_name(n) for n in names]
        assert len(set(normalized)) == 1
        assert normalized[0] == "blue pave 7"

    def test_different_products_normalize_differently(self):
        n1 = normalize_product_name("Blue Pavé 7")
        n2 = normalize_product_name("OG Kush")
        assert n1 != n2
