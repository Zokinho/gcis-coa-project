"""Tests for AI extractor response parsing (no API calls)."""

import pytest

from backend.services.ai_extractor import _parse_response


def test_parse_valid_json():
    raw = '''{
        "extraction": {
            "product_name": "Blue Pavé 7",
            "lot_number": "T-003-23-BP7",
            "lab": "Eurofins",
            "potency": {"total_thc_pct": 24.545}
        },
        "redaction_regions": [
            {"x_pct": 10, "y_pct": 20, "w_pct": 30, "h_pct": 5, "reason": "Client name", "confidence": "high"}
        ]
    }'''
    result = _parse_response(raw, page_number=0)
    assert result.product_name == "Blue Pavé 7"
    assert result.lot_number == "T-003-23-BP7"
    assert result.potency["total_thc_pct"] == 24.545
    assert len(result.redaction_regions) == 1
    assert result.redaction_regions[0]["page"] == 0


def test_parse_with_markdown_fences():
    raw = '''```json
{
    "extraction": {
        "product_name": "Test Strain",
        "lab": "TestLab"
    },
    "redaction_regions": []
}
```'''
    result = _parse_response(raw, page_number=2)
    assert result.product_name == "Test Strain"
    assert result.page == 2
    assert len(result.redaction_regions) == 0


def test_parse_invalid_json():
    raw = "This is not JSON at all"
    result = _parse_response(raw, page_number=0)
    assert result.product_name is None
    assert result.page == 0


def test_parse_empty_extraction():
    raw = '{"extraction": {}, "redaction_regions": []}'
    result = _parse_response(raw, page_number=1)
    assert result.product_name is None
    assert result.page == 1


def test_parse_null_fields():
    raw = '''{
        "extraction": {
            "product_name": "Test",
            "strain_type": null,
            "potency": null,
            "terpenes": {"total_pct": 1.5, "individual": [{"name": "Limonene", "value": 0.5, "unit": "%"}]}
        },
        "redaction_regions": []
    }'''
    result = _parse_response(raw, page_number=0)
    assert result.product_name == "Test"
    assert result.strain_type is None
    assert result.potency is None
    assert result.terpenes is not None
