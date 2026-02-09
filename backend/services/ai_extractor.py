"""AI extractor — uses Claude Vision API to extract product data and identify redaction regions."""

import base64
import json
import logging
from pathlib import Path

import anthropic

from backend.config import settings
from backend.models import ExtractionResult

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are analyzing a page from a cannabis Certificate of Analysis (CoA).
Perform TWO tasks and return the results as a single JSON object.

## Task 1: Extract Product Data

Extract all available data from this page. Not every page will have every field — extract only what is present.

Fields to look for:
- product_name: The product/strain name
- strain_type: indica, sativa, hybrid (if stated)
- lot_number: Lot/batch number
- producer: Producer/cultivator name (NOT the client/buyer)
- lab: Testing laboratory name
- test_date: Date of testing (ISO format YYYY-MM-DD if possible)
- report_number: Lab report/certificate number
- compliance_status: Overall PASS/FAIL if shown

Test sections (extract whichever are on this page):
- potency: Cannabinoid results. Include total_thc_pct, total_cbd_pct, and individual cannabinoids as a list with {name, value, unit}
- terpenes: Terpene profile. Include total_pct and individual terpenes as a list with {name, value, unit}
- microbial: Microbial testing results with {analyte, result, limit, unit, status}
- pesticides: Pesticide panel with {analyte, result, limit, unit, status}
- heavy_metals: Heavy metal results with {analyte, result, limit, unit, status}
- residual_solvents: Residual solvent results with {analyte, result, limit, unit, status}
- mycotoxins: Mycotoxin/aflatoxin results with {analyte, result, limit, unit, status}
- moisture: Moisture/water activity with {parameter, value, unit}

Also extract:
- methodologies: List of test methods mentioned (e.g., "HPLC", "GC-MS/MS")
- accreditations: Lab accreditations mentioned (e.g., "ISO 17025")
- lab_notes: Any notes, disclaimers, or comments

## Task 2: Identify Client Information to Redact

Identify ANY client/buyer information and QR codes that should be redacted.
This includes:
- Client company name
- Client address (street, city, postal code)
- Client account numbers, license numbers, PO numbers
- "Submitted By", "Ship To", "Bill To" information
- Client contact person names, phone numbers, emails
- ALL QR codes and barcodes (these may link to the original report with client info)

Do NOT flag for redaction:
- The laboratory name or address
- The product name or lot number
- Test results or methodology information
- Report numbers or dates

For each region to redact, provide bounding box coordinates as PERCENTAGES of the page dimensions (0-100):
- x_pct: left edge as % of page width
- y_pct: top edge as % of page height
- w_pct: width as % of page width
- h_pct: height as % of page height

## Response Format

Return ONLY a JSON object (no markdown fences, no explanation):

{
  "extraction": {
    "product_name": "...",
    "strain_type": "...",
    "lot_number": "...",
    "producer": "...",
    "lab": "...",
    "test_date": "...",
    "report_number": "...",
    "compliance_status": "...",
    "potency": { ... },
    "terpenes": { ... },
    "microbial": { ... },
    "pesticides": { ... },
    "heavy_metals": { ... },
    "residual_solvents": { ... },
    "mycotoxins": { ... },
    "moisture": { ... },
    "methodologies": [],
    "accreditations": [],
    "lab_notes": "..."
  },
  "redaction_regions": [
    {
      "x_pct": 10.5,
      "y_pct": 20.3,
      "w_pct": 30.0,
      "h_pct": 5.2,
      "reason": "Client company name",
      "confidence": "high"
    }
  ]
}

Only include fields that have data on this page. Use null for fields not present on this page.
For redaction_regions, return an empty list [] if no client information is found on this page."""


def extract_page(image_path: Path, page_number: int) -> ExtractionResult:
    """Send a single page image to Claude Vision API for extraction and redaction identification.

    Args:
        image_path: Path to the page image (PNG).
        page_number: Zero-indexed page number.

    Returns:
        ExtractionResult with extracted data and redaction regions.
    """
    logger.info("Extracting page %d: %s", page_number, image_path.name)

    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model=settings.vision_model,
            max_tokens=settings.vision_max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
        )
    except anthropic.APIError as e:
        logger.error("Claude API error on page %d: %s", page_number, e)
        return ExtractionResult(page=page_number)

    raw_text = response.content[0].text
    logger.debug("Raw API response for page %d: %s", page_number, raw_text[:500])

    return _parse_response(raw_text, page_number)


def _parse_response(raw_text: str, page_number: int) -> ExtractionResult:
    """Parse the JSON response from Claude, handling markdown fences."""
    # Strip markdown code fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        # Remove opening fence (possibly ```json)
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from page %d: %s\nRaw: %s", page_number, e, raw_text)
        return ExtractionResult(page=page_number)

    extraction = data.get("extraction", {})
    redaction_regions = data.get("redaction_regions", [])

    # Add page number to each redaction region
    for region in redaction_regions:
        region["page"] = page_number

    result = ExtractionResult(
        page=page_number,
        product_name=extraction.get("product_name"),
        strain_type=extraction.get("strain_type"),
        lot_number=extraction.get("lot_number"),
        producer=extraction.get("producer"),
        lab=extraction.get("lab"),
        test_date=extraction.get("test_date"),
        report_number=extraction.get("report_number"),
        compliance_status=extraction.get("compliance_status"),
        potency=extraction.get("potency"),
        terpenes=extraction.get("terpenes"),
        microbial=extraction.get("microbial"),
        pesticides=extraction.get("pesticides"),
        heavy_metals=extraction.get("heavy_metals"),
        residual_solvents=extraction.get("residual_solvents"),
        mycotoxins=extraction.get("mycotoxins"),
        moisture=extraction.get("moisture"),
        methodologies=extraction.get("methodologies") or [],
        accreditations=extraction.get("accreditations") or [],
        lab_notes=extraction.get("lab_notes"),
        redaction_regions=redaction_regions,
    )

    logger.info(
        "Page %d: product=%s, lot=%s, %d redaction regions",
        page_number, result.product_name, result.lot_number, len(redaction_regions),
    )
    return result


def extract_all_pages(image_paths: list[Path]) -> list[ExtractionResult]:
    """Extract data from all pages sequentially.

    Sequential to respect API rate limits and keep costs predictable.
    """
    results = []
    for i, path in enumerate(image_paths):
        result = extract_page(path, i)
        results.append(result)
    return results
