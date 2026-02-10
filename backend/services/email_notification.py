"""Email notification service — sends admin alerts via SMTP and logs to DB."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from backend.config import settings
from backend.database import SessionLocal
from backend.models import NotificationLog, NotificationType

logger = logging.getLogger(__name__)


# ── Config check ──────────────────────────────────────────────────


def _check_config() -> str | None:
    """Return an error message if notifications are not properly configured, else None."""
    if not settings.notifications_enabled:
        return "Notifications are disabled"
    if not settings.smtp_host:
        return "SMTP_HOST not configured"
    if not settings.smtp_user or not settings.smtp_password:
        return "SMTP credentials not configured"
    if not settings.notification_admin_email:
        return "NOTIFICATION_ADMIN_EMAIL not configured"
    if not settings.smtp_from_email:
        return "SMTP_FROM_EMAIL not configured"
    return None


# ── HTML templates ────────────────────────────────────────────────


def _job_ready_html(job_id: str, filename: str, product_name: str) -> str:
    """HTML email body for a job ready for review."""
    return f"""\
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
  <h2 style="color: #2c7a2c;">CoA Ready for Review</h2>
  <table style="border-collapse: collapse; margin: 16px 0;">
    <tr><td style="padding: 4px 12px; font-weight: bold;">Job ID</td><td style="padding: 4px 12px;">{job_id}</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">Filename</td><td style="padding: 4px 12px;">{filename}</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">Product</td><td style="padding: 4px 12px;">{product_name or '(unknown)'}</td></tr>
  </table>
  <p>Log in to the admin dashboard to review redactions and publish.</p>
  <hr style="border: none; border-top: 1px solid #ddd;">
  <p style="font-size: 12px; color: #888;">GCIS CoA Automation</p>
</body>
</html>"""


def _new_email_html(
    ingestion_id: str,
    subject: str,
    sender: str,
    attachment_count: int,
    coa_count: int,
) -> str:
    """HTML email body for a newly ingested email."""
    return f"""\
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
  <h2 style="color: #2a6496;">New Email Ingested</h2>
  <table style="border-collapse: collapse; margin: 16px 0;">
    <tr><td style="padding: 4px 12px; font-weight: bold;">Ingestion ID</td><td style="padding: 4px 12px;">{ingestion_id}</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">Subject</td><td style="padding: 4px 12px;">{subject}</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">From</td><td style="padding: 4px 12px;">{sender}</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">Attachments</td><td style="padding: 4px 12px;">{attachment_count}</td></tr>
    <tr><td style="padding: 4px 12px; font-weight: bold;">CoAs detected</td><td style="padding: 4px 12px;">{coa_count}</td></tr>
  </table>
  <p>Log in to the admin inbox to review and confirm the client.</p>
  <hr style="border: none; border-top: 1px solid #ddd;">
  <p style="font-size: 12px; color: #888;">GCIS CoA Automation</p>
</body>
</html>"""


# ── SMTP send ─────────────────────────────────────────────────────


async def _send_smtp(recipient: str, subject: str, body_html: str) -> None:
    """Send an HTML email via SMTP (async)."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=settings.smtp_use_tls,
    )


# ── DB logging ────────────────────────────────────────────────────


def _log_notification(
    notification_type: NotificationType,
    recipient: str,
    subject: str,
    body_html: str,
    related_id: str | None,
    success: bool,
    error_message: str | None = None,
) -> None:
    """Write a NotificationLog entry (uses its own session to avoid cross-thread issues)."""
    db = SessionLocal()
    try:
        log = NotificationLog(
            notification_type=notification_type,
            recipient=recipient,
            subject=subject,
            body_html=body_html,
            related_id=related_id,
            success=success,
            error_message=error_message,
        )
        db.add(log)
        db.commit()
    except Exception:
        logger.exception("Failed to log notification")
    finally:
        db.close()


# ── Public API ────────────────────────────────────────────────────


async def notify_job_ready(job_id: str, filename: str, product_name: str) -> bool:
    """Send a 'job ready for review' notification. Returns True on success."""
    config_error = _check_config()
    if config_error:
        logger.debug("Skipping job-ready notification: %s", config_error)
        return False

    recipient = settings.notification_admin_email
    subject = f"CoA Ready for Review: {filename}"
    body_html = _job_ready_html(job_id, filename, product_name)

    try:
        await _send_smtp(recipient, subject, body_html)
        _log_notification(
            NotificationType.job_ready_for_review, recipient, subject,
            body_html, related_id=job_id, success=True,
        )
        logger.info("[%s] Job-ready notification sent to %s", job_id, recipient)
        return True
    except Exception as e:
        logger.exception("[%s] Failed to send job-ready notification", job_id)
        _log_notification(
            NotificationType.job_ready_for_review, recipient, subject,
            body_html, related_id=job_id, success=False, error_message=str(e),
        )
        return False


async def notify_new_email(
    ingestion_id: str,
    subject: str,
    sender: str,
    attachment_count: int,
    coa_count: int,
) -> bool:
    """Send a 'new email ingested' notification. Returns True on success."""
    config_error = _check_config()
    if config_error:
        logger.debug("Skipping new-email notification: %s", config_error)
        return False

    recipient = settings.notification_admin_email
    email_subject = f"New Email Ingested: {subject}"
    body_html = _new_email_html(ingestion_id, subject, sender, attachment_count, coa_count)

    try:
        await _send_smtp(recipient, email_subject, body_html)
        _log_notification(
            NotificationType.new_email_ingested, recipient, email_subject,
            body_html, related_id=ingestion_id, success=True,
        )
        logger.info("[%s] New-email notification sent to %s", ingestion_id, recipient)
        return True
    except Exception as e:
        logger.exception("[%s] Failed to send new-email notification", ingestion_id)
        _log_notification(
            NotificationType.new_email_ingested, recipient, email_subject,
            body_html, related_id=ingestion_id, success=False, error_message=str(e),
        )
        return False
