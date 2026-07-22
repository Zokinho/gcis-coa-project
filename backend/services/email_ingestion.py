"""IMAP email ingestion — polls inbox for CoA emails, classifies attachments, triggers pipeline."""

import email
import email.utils
import imaplib
import json
import logging
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

import anthropic
from PIL import Image
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import (
    AttachmentType,
    CoAJob,
    EmailAttachment,
    EmailIngestion,
    EmailIngestionStatus,
    JobStatus,
)
from backend.tasks.dispatch import send_process_coa

logger = logging.getLogger(__name__)

_stop_event = threading.Event()
_poller_thread: threading.Thread | None = None


# ── Sender validation ───────────────────────────────────────────


def _is_sender_allowed(sender: str) -> bool:
    """Check if the sender is in the configured allowlist.

    Returns True if no allowlist is configured (accept all) or if the
    sender's email address or domain matches an entry in the allowlist.
    """
    allowlist = settings.sender_allowlist
    if not allowlist:
        return True

    # Extract email from "Name <email@domain.com>" format
    match = re.search(r"<([^>]+)>", sender)
    addr = match.group(1).strip().lower() if match else sender.strip().lower()

    if not addr or "@" not in addr:
        return False

    domain = "@" + addr.split("@", 1)[1]

    for entry in allowlist:
        if entry == addr or entry == domain:
            return True

    return False


# ── Attachment classification ────────────────────────────────────

COA_KEYWORDS = re.compile(r"(?i)(coa|certificate|analysis|lab.?report|test.?result)")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
PDF_EXTENSION = ".pdf"


def classify_attachment(filename: str) -> AttachmentType:
    """Classify an attachment based on filename heuristics."""
    ext = Path(filename).suffix.lower()
    if ext == PDF_EXTENSION:
        return AttachmentType.coa_pdf
    if ext in IMAGE_EXTENSIONS:
        if COA_KEYWORDS.search(filename):
            return AttachmentType.coa_photo
        return AttachmentType.product_photo
    # Unknown extension — treat as product photo
    return AttachmentType.product_photo


# ── AI client suggestion ─────────────────────────────────────────


def suggest_client_from_email(subject: str, sender: str, body: str) -> str | None:
    """Use Claude to suggest the client/company name from email metadata."""
    if not settings.anthropic_api_key:
        return None

    prompt = (
        "You are given an email that was forwarded to a cannabis CoA (Certificate of Analysis) inbox.\n"
        "Your task: extract the client or company name this email is about.\n"
        "Return ONLY the company name, nothing else. If you can't determine it, return 'Unknown'.\n\n"
        f"Subject: {subject}\n"
        f"Sender: {sender}\n"
        f"Body (first 1000 chars):\n{body[:1000] if body else '(empty)'}"
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        result = response.content[0].text.strip()
        return result if result and result.lower() != "unknown" else None
    except Exception:
        logger.exception("AI client suggestion failed")
        return None


# ── AI product extraction from email body ────────────────────────


def extract_products_from_email(subject: str, sender: str, body: str) -> list[dict] | None:
    """Use Claude to extract product data from email body text."""
    if not settings.anthropic_api_key or not body.strip():
        return None

    prompt = (
        "You are analyzing an email forwarded to a cannabis inventory inbox.\n"
        "Extract ALL cannabis products mentioned in the email.\n\n"
        "For each product, extract whatever fields you can find:\n"
        "- product_name: strain or product name\n"
        "- strain_type: Indica, Sativa, Hybrid, or null\n"
        "- producer: licensed producer / LP / grower name\n"
        "- thc_percent: THC percentage (number only)\n"
        "- cbd_percent: CBD percentage (number only)\n"
        "- price_per_gram: price per gram in CAD (number only)\n"
        "- quantity_grams: available quantity in grams (number only)\n"
        "- lot_number: lot or batch number\n"
        "- category: Flower, Pre-Roll, Extract, Edible, Vape, etc.\n"
        "- notes: any other relevant details (terpenes, harvest date, etc.)\n\n"
        "Return a JSON array of product objects. If no products found, return [].\n"
        "Return ONLY the JSON array, no other text.\n\n"
        f"Subject: {subject}\n"
        f"Sender: {sender}\n"
        f"Email body:\n{body[:8000]}"
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Handle markdown fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        products = json.loads(text)
        return products if isinstance(products, list) else None
    except Exception:
        logger.exception("AI product extraction from email failed")
        return None


# ── Image → PDF conversion ───────────────────────────────────────


def image_to_pdf(image_path: Path, output_path: Path) -> Path:
    """Convert an image file to a single-page PDF via Pillow."""
    img = Image.open(image_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(output_path, "PDF", resolution=200)
    return output_path


# ── Email parsing ────────────────────────────────────────────────


def _parse_date(msg: email.message.Message) -> datetime | None:
    """Parse the Date header into a datetime."""
    date_str = msg.get("Date")
    if not date_str:
        return None
    parsed = email.utils.parsedate_to_datetime(date_str)
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def _extract_body(msg: email.message.Message) -> str:
    """Extract body from an email — prefers plain text, falls back to HTML conversion."""
    import html2text

    plain = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if part.get("Content-Disposition") == "attachment":
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if ct == "text/plain" and not plain:
                plain = text
            elif ct == "text/html" and not html_body:
                html_body = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html_body = text
            else:
                plain = text

    if plain:
        return plain

    if html_body:
        converter = html2text.HTML2Text()
        converter.ignore_links = True
        converter.ignore_images = True
        converter.body_width = 0  # no line wrapping
        return converter.handle(html_body)

    return ""


def _extract_attachments(msg: email.message.Message) -> list[tuple[str, bytes]]:
    """Extract (filename, data) pairs from email attachments."""
    attachments = []
    for part in msg.walk():
        disp = part.get("Content-Disposition")
        if disp is None:
            continue
        if "attachment" not in disp.lower() and "inline" not in disp.lower():
            continue
        filename = part.get_filename()
        if not filename:
            continue
        data = part.get_payload(decode=True)
        if data:
            max_size = settings.max_pdf_file_size_mb * 1024 * 1024
            if len(data) > max_size:
                logger.warning(
                    "Attachment %s too large (%d bytes, limit %d MB) — skipped",
                    filename, len(data), settings.max_pdf_file_size_mb,
                )
                continue
            attachments.append((filename, data))
    return attachments


# ── Core polling logic ───────────────────────────────────────────


def _process_single_email(msg: email.message.Message, db: Session) -> EmailIngestion | None:
    """Parse one email message, create records, and trigger CoA processing."""
    # Sender allowlist check
    sender_raw = msg.get("From", "")
    if not _is_sender_allowed(sender_raw):
        logger.warning("Email from non-allowed sender skipped: %s", sender_raw)
        return None

    message_id = msg.get("Message-ID", "")
    if not message_id:
        message_id = f"no-msgid-{uuid.uuid4()}"

    # Dedup check
    existing = db.query(EmailIngestion).filter(EmailIngestion.message_id == message_id).first()
    if existing:
        logger.debug("Duplicate email skipped: %s", message_id)
        return None

    subject = msg.get("Subject", "(no subject)")
    sender = msg.get("From", "")
    body = _extract_body(msg)
    received_at = _parse_date(msg)

    # Create ingestion record
    ingestion = EmailIngestion(
        message_id=message_id,
        subject=subject,
        sender=sender,
        body_text=body,
        received_at=received_at,
        status=EmailIngestionStatus.processing,
    )
    db.add(ingestion)
    db.flush()  # get ID

    # Save attachments
    attach_dir = settings.email_attachments_path / ingestion.id
    attach_dir.mkdir(parents=True, exist_ok=True)

    raw_attachments = _extract_attachments(msg)
    if not raw_attachments:
        # AI client suggestion + product extraction for attachment-less emails
        suggested = suggest_client_from_email(subject, sender, body)
        ingestion.suggested_client = suggested
        if body.strip():
            products = extract_products_from_email(subject, sender, body)
            if products:
                ingestion.extracted_products = products
                logger.info("Extracted %d products from email body (no attachments): %s", len(products), subject)
        ingestion.status = EmailIngestionStatus.review
        db.commit()
        try:
            from backend.tasks.notification_tasks import dispatch_new_email_notification
            dispatch_new_email_notification(ingestion.id, subject, sender, 0, 0)
        except Exception:
            logger.exception("Failed to dispatch new-email notification for %s", ingestion.id)
        return ingestion

    coa_attachments: list[EmailAttachment] = []

    for filename, data in raw_attachments:
        att_type = classify_attachment(filename)
        stored_name = f"{uuid.uuid4()}{Path(filename).suffix.lower()}"
        stored_path = attach_dir / stored_name

        stored_path.write_bytes(data)

        # Magic byte validation for PDFs
        if att_type == AttachmentType.coa_pdf and data[:5] != b"%PDF-":
            logger.warning(
                "Attachment %s has .pdf extension but invalid magic bytes — reclassified as product_photo",
                filename,
            )
            att_type = AttachmentType.product_photo

        attachment = EmailAttachment(
            email_ingestion_id=ingestion.id,
            original_filename=filename,
            stored_filename=stored_name,
            attachment_type=att_type,
            file_size=len(data),
        )
        db.add(attachment)
        db.flush()

        if att_type in (AttachmentType.coa_pdf, AttachmentType.coa_photo):
            coa_attachments.append(attachment)
        elif att_type == AttachmentType.product_photo:
            # Copy to photos directory
            photo_dir = settings.photos_path / ingestion.id
            photo_dir.mkdir(parents=True, exist_ok=True)
            (photo_dir / stored_name).write_bytes(data)

    # AI client suggestion
    suggested = suggest_client_from_email(subject, sender, body)
    ingestion.suggested_client = suggested

    # AI product extraction from email body
    if body.strip():
        products = extract_products_from_email(subject, sender, body)
        if products:
            ingestion.extracted_products = products
            logger.info("Extracted %d products from email body: %s", len(products), subject)

    # Process CoA attachments through pipeline
    for att in coa_attachments:
        source_path = attach_dir / att.stored_filename

        # For CoA photos, convert to PDF first
        if att.attachment_type == AttachmentType.coa_photo:
            pdf_name = f"{Path(att.stored_filename).stem}.pdf"
            pdf_path = settings.uploads_path / pdf_name
            image_to_pdf(source_path, pdf_path)
            upload_filename = pdf_name
        else:
            # Copy PDF to uploads
            upload_filename = att.stored_filename
            dest = settings.uploads_path / upload_filename
            dest.write_bytes(source_path.read_bytes())

        # Create CoAJob
        job = CoAJob(
            filename=upload_filename,
            status=JobStatus.queued,
            email_ingestion_id=ingestion.id,
        )
        db.add(job)
        db.flush()

        att.job_id = job.id

        # Dispatch to Celery (falls back to threading if Redis unavailable)
        send_process_coa(job.id)

    ingestion.status = EmailIngestionStatus.review
    db.commit()

    try:
        from backend.tasks.notification_tasks import dispatch_new_email_notification
        dispatch_new_email_notification(
            ingestion.id, subject, sender, len(raw_attachments), len(coa_attachments),
        )
    except Exception:
        logger.exception("Failed to dispatch new-email notification for %s", ingestion.id)

    logger.info("Processed email: %s (%d attachments, %d CoAs)", subject, len(raw_attachments), len(coa_attachments))
    return ingestion


def _get_oauth2_token() -> str:
    """Get an OAuth2 access token for IMAP using client credentials flow."""
    from azure.identity import ClientSecretCredential

    credential = ClientSecretCredential(
        settings.ms_tenant_id,
        settings.ms_client_id,
        settings.ms_client_secret,
    )
    token = credential.get_token("https://outlook.office365.com/.default")
    return token.token


def _build_xoauth2_string(user: str, token: str) -> str:
    """Build the XOAUTH2 authentication string for IMAP."""
    return f"user={user}\x01auth=Bearer {token}\x01\x01"


def poll_inbox_once() -> int:
    """Connect to IMAP, fetch UNSEEN messages, process them. Returns count of new emails."""
    if not settings.imap_host or not settings.imap_user:
        logger.warning("IMAP not configured, skipping poll")
        return 0

    db = SessionLocal()
    count = 0
    conn = None
    try:
        # Connect
        if settings.imap_use_ssl:
            conn = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        else:
            conn = imaplib.IMAP4(settings.imap_host, settings.imap_port)

        if settings.imap_use_oauth2:
            token = _get_oauth2_token()
            auth_string = _build_xoauth2_string(settings.imap_user, token)
            conn.authenticate("XOAUTH2", lambda x: auth_string.encode())
        else:
            conn.login(settings.imap_user, settings.imap_password)
        conn.select(settings.imap_folder)

        # Search for unseen
        status, data = conn.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            return 0

        msg_nums = data[0].split()
        logger.info("Found %d unseen emails", len(msg_nums))

        for num in msg_nums:
            if _stop_event.is_set():
                break
            try:
                status, msg_data = conn.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                result = _process_single_email(msg, db)
                if result:
                    count += 1
                # Mark as SEEN
                conn.store(num, "+FLAGS", "\\Seen")
            except Exception:
                logger.exception("Failed to process email #%s", num)

    except Exception:
        logger.exception("IMAP polling error")
    finally:
        if conn:
            try:
                conn.close()
                conn.logout()
            except Exception:
                pass
        db.close()

    logger.info("Processed %d new emails", count)
    return count


# ── Background poller ────────────────────────────────────────────


def _poller_loop():
    """Daemon thread loop that polls the inbox on an interval."""
    logger.info("Email poller started (interval=%ds)", settings.imap_poll_interval_seconds)
    while not _stop_event.is_set():
        try:
            poll_inbox_once()
        except Exception:
            logger.exception("Unhandled error in email poller")
        _stop_event.wait(timeout=settings.imap_poll_interval_seconds)
    logger.info("Email poller stopped")


def start_email_poller():
    """Start the background IMAP poller if enabled and configured."""
    global _poller_thread
    if not settings.email_ingestion_enabled:
        logger.info("Email ingestion disabled")
        return
    if not settings.imap_host or not settings.imap_user:
        logger.warning("Email ingestion enabled but IMAP not configured")
        return
    _stop_event.clear()
    _poller_thread = threading.Thread(target=_poller_loop, daemon=True)
    _poller_thread.start()


def stop_email_poller():
    """Signal the poller to stop."""
    _stop_event.set()
