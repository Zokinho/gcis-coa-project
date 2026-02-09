"""Merge extraction results from multiple CoA pages into a single product record."""

import logging
from backend.models import ExtractionResult

logger = logging.getLogger(__name__)

# Test sections that appear once across the CoA
TEST_SECTIONS = [
    "potency", "terpenes", "microbial", "pesticides",
    "heavy_metals", "residual_solvents", "mycotoxins", "moisture",
]

# Simple scalar fields — take first non-null value
SCALAR_FIELDS = [
    "product_name", "strain_type", "lot_number", "producer",
    "lab", "test_date", "report_number", "compliance_status",
]


def merge_extractions(pages: list[ExtractionResult]) -> ExtractionResult:
    """Merge extraction results from multiple pages into one combined result.

    Strategy:
    - Scalar fields: take first non-null value encountered
    - Test sections: take from whichever page has the data
    - List fields (methodologies, accreditations): accumulate unique entries
    - Lab notes: concatenate from all pages
    - Redaction regions: collect all, preserving page numbers
    """
    if not pages:
        return ExtractionResult()

    if len(pages) == 1:
        return pages[0]

    merged = ExtractionResult()

    # Scalar fields — first non-null wins
    for field in SCALAR_FIELDS:
        for page in pages:
            val = getattr(page, field, None)
            if val:
                setattr(merged, field, val)
                break

    # Test sections — take from whichever page has data
    for section in TEST_SECTIONS:
        for page in pages:
            val = getattr(page, section, None)
            if val:
                setattr(merged, section, val)
                break

    # Accumulate list fields (deduplicated, order-preserving)
    seen_methods: set[str] = set()
    seen_accreds: set[str] = set()
    for page in pages:
        for m in page.methodologies:
            if m not in seen_methods:
                seen_methods.add(m)
                merged.methodologies.append(m)
        for a in page.accreditations:
            if a not in seen_accreds:
                seen_accreds.add(a)
                merged.accreditations.append(a)

    # Concatenate lab notes
    notes = [p.lab_notes for p in pages if p.lab_notes]
    if notes:
        merged.lab_notes = "\n".join(notes)

    # Collect all redaction regions (already have page numbers)
    for page in pages:
        merged.redaction_regions.extend(page.redaction_regions)

    logger.info(
        "Merged %d pages → product=%s, lot=%s, %d redactions",
        len(pages), merged.product_name, merged.lot_number, len(merged.redaction_regions),
    )
    return merged


def generate_tags(merged: ExtractionResult) -> list[str]:
    """Auto-generate searchable tags from the merged extraction."""
    tags: list[str] = []

    # THC level tags
    if merged.potency and isinstance(merged.potency, dict):
        thc = merged.potency.get("total_thc_pct") or merged.potency.get("total_thc")
        if thc is not None:
            try:
                thc_val = float(str(thc).replace("%", "").strip())
                if thc_val >= 25:
                    tags.append("high-thc")
                elif thc_val >= 20:
                    tags.append("mid-thc")
                elif thc_val >= 10:
                    tags.append("low-thc")
            except (ValueError, TypeError):
                pass

    # Dominant terpene tag
    if merged.terpenes and isinstance(merged.terpenes, dict):
        terpene_list = merged.terpenes.get("individual") or merged.terpenes.get("terpenes")
        if isinstance(terpene_list, list) and terpene_list:
            # Find highest terpene
            best = max(terpene_list, key=lambda t: _parse_float(t.get("value", 0)))
            name = best.get("name", "").lower().replace(" ", "-").replace("d-", "").replace("β-", "beta-")
            if name:
                tags.append(f"{name}-dominant")
        elif isinstance(terpene_list, dict):
            # Handle dict format {name: value}
            if terpene_list:
                best_name = max(terpene_list, key=lambda k: _parse_float(terpene_list[k]))
                tags.append(f"{best_name.lower().replace(' ', '-')}-dominant")

    # Compliance
    if merged.compliance_status and "pass" in merged.compliance_status.lower():
        tags.append("compliant")

    # Full panel check
    sections_present = sum(1 for s in TEST_SECTIONS if getattr(merged, s))
    if sections_present >= 5:
        tags.append("full-panel")

    # Strain type
    if merged.strain_type:
        tags.append(merged.strain_type.lower())

    return tags


def _parse_float(val) -> float:
    try:
        return float(str(val).replace("%", "").replace("<", "").replace(">", "").strip())
    except (ValueError, TypeError):
        return 0.0
