"""Redactor — applies white-box redactions to PDF page images and reassembles into a PDF."""

import logging
from pathlib import Path

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# Padding around redaction regions (as % of page dimensions)
PADDING_PCT = 0.5


def apply_redactions(
    page_images: list[Path],
    redaction_regions: list[dict],
    output_path: Path,
) -> Path:
    """Apply white-box redactions to page images and save as a new PDF.

    Args:
        page_images: Paths to page PNG images (in order).
        redaction_regions: List of dicts with keys: page, x_pct, y_pct, w_pct, h_pct, approved.
        output_path: Where to save the redacted PDF.

    Returns:
        Path to the saved redacted PDF.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Group redactions by page
    by_page: dict[int, list[dict]] = {}
    for region in redaction_regions:
        if not region.get("approved", True):
            continue
        page = region["page"]
        by_page.setdefault(page, []).append(region)

    redacted_pages: list[Image.Image] = []

    for i, img_path in enumerate(page_images):
        img = Image.open(img_path).convert("RGB")

        if i in by_page:
            draw = ImageDraw.Draw(img)
            w, h = img.size

            for region in by_page[i]:
                x = (region["x_pct"] - PADDING_PCT) / 100 * w
                y = (region["y_pct"] - PADDING_PCT) / 100 * h
                rw = (region["w_pct"] + 2 * PADDING_PCT) / 100 * w
                rh = (region["h_pct"] + 2 * PADDING_PCT) / 100 * h

                # Clamp to image bounds
                x = max(0, x)
                y = max(0, y)
                x2 = min(w, x + rw)
                y2 = min(h, y + rh)

                draw.rectangle([x, y, x2, y2], fill="white")
                logger.debug("Redacted page %d: (%.1f,%.1f)-(%.1f,%.1f) — %s",
                             i, x, y, x2, y2, region.get("reason", ""))

            logger.info("Applied %d redactions to page %d", len(by_page[i]), i)

        redacted_pages.append(img)

    if not redacted_pages:
        logger.warning("No pages to redact")
        return output_path

    # Save all pages as a single PDF
    first = redacted_pages[0]
    if len(redacted_pages) > 1:
        first.save(output_path, "PDF", save_all=True, append_images=redacted_pages[1:])
    else:
        first.save(output_path, "PDF")

    logger.info("Saved redacted PDF: %s (%d pages)", output_path, len(redacted_pages))
    return output_path
