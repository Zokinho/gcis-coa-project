"""Convert PDF pages to images for Vision API processing."""

import logging
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image

from backend.config import settings

logger = logging.getLogger(__name__)


def convert_pdf_to_images(pdf_path: Path, output_dir: Path) -> list[Path]:
    """Convert each page of a PDF to a PNG image.

    Images are resized so the longest side does not exceed settings.max_image_dimension.

    Returns:
        List of paths to the generated page images.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    max_dim = settings.max_image_dimension

    logger.info("Converting PDF to images: %s", pdf_path.name)
    pages = convert_from_path(pdf_path, dpi=200, timeout=settings.pdf_conversion_timeout_seconds)
    logger.info("PDF has %d pages", len(pages))

    if len(pages) > settings.max_pdf_page_count:
        raise ValueError(
            f"PDF has {len(pages)} pages, exceeding limit of {settings.max_pdf_page_count}"
        )

    image_paths: list[Path] = []
    for i, page in enumerate(pages):
        # Resize if needed
        page = _resize_image(page, max_dim)

        out_path = output_dir / f"page_{i}.png"
        page.save(out_path, "PNG")
        image_paths.append(out_path)
        logger.debug("Saved page %d: %s (%dx%d)", i, out_path.name, page.width, page.height)

    return image_paths


def _resize_image(img: Image.Image, max_dim: int) -> Image.Image:
    """Resize image so its longest side is at most max_dim, preserving aspect ratio."""
    w, h = img.size
    longest = max(w, h)
    if longest <= max_dim:
        return img

    scale = max_dim / longest
    new_w = int(w * scale)
    new_h = int(h * scale)
    return img.resize((new_w, new_h), Image.LANCZOS)
