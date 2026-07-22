"""PDF unlock service — removes owner passwords using pikepdf."""

import logging
from pathlib import Path

import pikepdf

from backend.config import settings

logger = logging.getLogger(__name__)


def unlock_pdf(input_path: Path, output_path: Path) -> tuple[bool, bool, str | None]:
    """Attempt to unlock a PDF by removing owner-level restrictions.

    Returns:
        (success, was_locked, error_message)
        - success: True if the file is now usable (unlocked or was never locked)
        - was_locked: True if the original had an owner password that was removed
        - error_message: Description of failure, or None on success
    """
    # Magic byte validation
    try:
        with open(input_path, "rb") as f:
            magic = f.read(5)
        if magic != b"%PDF-":
            logger.warning("File is not a valid PDF (bad magic bytes): %s", input_path.name)
            return False, False, "File is not a valid PDF (bad magic bytes)"
    except Exception as e:
        logger.error("Failed to read file %s: %s", input_path.name, e)
        return False, False, f"Failed to read file: {e}"

    try:
        # Try opening with empty password — works for owner-password-only PDFs
        pdf = pikepdf.open(input_path, password="")
    except pikepdf.PasswordError:
        logger.warning("PDF requires user password: %s", input_path.name)
        return False, True, "PDF is user-password protected — requires manual handling"
    except Exception as e:
        logger.error("Failed to open PDF %s: %s", input_path.name, e)
        return False, False, f"Failed to open PDF: {e}"

    # Page count check
    page_count = len(pdf.pages)
    if page_count > settings.max_pdf_page_count:
        pdf.close()
        msg = f"PDF has {page_count} pages, exceeding limit of {settings.max_pdf_page_count}"
        logger.warning("%s: %s", msg, input_path.name)
        return False, False, msg

    was_locked = pdf.is_encrypted

    try:
        # Save without encryption to remove owner password restrictions
        pdf.save(output_path)
        pdf.close()
        logger.info(
            "PDF %s: %s",
            "unlocked" if was_locked else "copied (no lock)",
            input_path.name,
        )
        return True, was_locked, None
    except Exception as e:
        pdf.close()
        logger.error("Failed to save unlocked PDF %s: %s", input_path.name, e)
        return False, was_locked, f"Failed to save unlocked PDF: {e}"
