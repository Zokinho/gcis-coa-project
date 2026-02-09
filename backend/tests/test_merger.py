"""Tests for multi-page extraction merger."""

from backend.models import ExtractionResult
from backend.services.merger import merge_extractions, generate_tags


def test_merge_single_page():
    page = ExtractionResult(
        page=0,
        product_name="Blue Pavé 7",
        lot_number="T-003-23-BP7",
    )
    result = merge_extractions([page])
    assert result.product_name == "Blue Pavé 7"


def test_merge_scalar_first_wins():
    pages = [
        ExtractionResult(page=0, product_name="Blue Pavé 7", lab="Eurofins"),
        ExtractionResult(page=1, product_name="Blue Pave 7", lab="Eurofins Lab"),
    ]
    result = merge_extractions(pages)
    assert result.product_name == "Blue Pavé 7"
    assert result.lab == "Eurofins"


def test_merge_test_sections():
    pages = [
        ExtractionResult(page=0, potency={"total_thc_pct": 24.5}),
        ExtractionResult(page=1, terpenes={"total_pct": 1.2}),
        ExtractionResult(page=2, pesticides={"result": "PASS"}),
    ]
    result = merge_extractions(pages)
    assert result.potency is not None
    assert result.terpenes is not None
    assert result.pesticides is not None
    assert result.microbial is None


def test_merge_redaction_regions():
    pages = [
        ExtractionResult(page=0, redaction_regions=[
            {"page": 0, "x_pct": 10, "y_pct": 20, "w_pct": 30, "h_pct": 5, "reason": "Client name"}
        ]),
        ExtractionResult(page=1, redaction_regions=[]),
        ExtractionResult(page=2, redaction_regions=[
            {"page": 2, "x_pct": 5, "y_pct": 10, "w_pct": 20, "h_pct": 3, "reason": "Address"}
        ]),
    ]
    result = merge_extractions(pages)
    assert len(result.redaction_regions) == 2


def test_merge_methodologies_deduplicated():
    pages = [
        ExtractionResult(page=0, methodologies=["HPLC", "GC-MS"]),
        ExtractionResult(page=1, methodologies=["GC-MS", "ICP-MS"]),
    ]
    result = merge_extractions(pages)
    assert result.methodologies == ["HPLC", "GC-MS", "ICP-MS"]


def test_generate_tags_high_thc():
    merged = ExtractionResult(
        potency={"total_thc_pct": 26.0},
        compliance_status="PASS",
    )
    tags = generate_tags(merged)
    assert "high-thc" in tags
    assert "compliant" in tags


def test_generate_tags_terpene_dominant():
    merged = ExtractionResult(
        terpenes={
            "individual": [
                {"name": "d-Limonene", "value": 0.38, "unit": "%"},
                {"name": "Linalool", "value": 0.23, "unit": "%"},
            ]
        }
    )
    tags = generate_tags(merged)
    assert any("limonene" in t for t in tags)


def test_merge_empty():
    result = merge_extractions([])
    assert result.product_name is None
