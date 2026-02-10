"""Tests for email notification service and dispatch helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.email_notification import (
    _check_config,
    _job_ready_html,
    _new_email_html,
    notify_job_ready,
    notify_new_email,
)


# ── Config validation ─────────────────────────────────────────────


def test_check_config_disabled():
    with patch("backend.services.email_notification.settings") as s:
        s.notifications_enabled = False
        assert _check_config() == "Notifications are disabled"


def test_check_config_no_host():
    with patch("backend.services.email_notification.settings") as s:
        s.notifications_enabled = True
        s.smtp_host = ""
        assert "SMTP_HOST" in _check_config()


def test_check_config_no_creds():
    with patch("backend.services.email_notification.settings") as s:
        s.notifications_enabled = True
        s.smtp_host = "smtp.example.com"
        s.smtp_user = ""
        s.smtp_password = ""
        assert "credentials" in _check_config()


def test_check_config_no_admin_email():
    with patch("backend.services.email_notification.settings") as s:
        s.notifications_enabled = True
        s.smtp_host = "smtp.example.com"
        s.smtp_user = "user"
        s.smtp_password = "pass"
        s.notification_admin_email = ""
        assert "NOTIFICATION_ADMIN_EMAIL" in _check_config()


def test_check_config_no_from_email():
    with patch("backend.services.email_notification.settings") as s:
        s.notifications_enabled = True
        s.smtp_host = "smtp.example.com"
        s.smtp_user = "user"
        s.smtp_password = "pass"
        s.notification_admin_email = "admin@test.com"
        s.smtp_from_email = ""
        assert "SMTP_FROM_EMAIL" in _check_config()


def test_check_config_ok():
    with patch("backend.services.email_notification.settings") as s:
        s.notifications_enabled = True
        s.smtp_host = "smtp.example.com"
        s.smtp_user = "user"
        s.smtp_password = "pass"
        s.notification_admin_email = "admin@test.com"
        s.smtp_from_email = "noreply@test.com"
        assert _check_config() is None


# ── HTML templates ────────────────────────────────────────────────


def test_job_ready_html_content():
    html = _job_ready_html("job-123", "test.pdf", "Blue Pavé 7")
    assert "job-123" in html
    assert "test.pdf" in html
    assert "Blue Pavé 7" in html
    assert "Ready for Review" in html


def test_job_ready_html_unknown_product():
    html = _job_ready_html("job-456", "report.pdf", "")
    assert "(unknown)" in html


def test_new_email_html_content():
    html = _new_email_html("ing-789", "FW: Lab Results", "lab@example.com", 3, 2)
    assert "ing-789" in html
    assert "FW: Lab Results" in html
    assert "lab@example.com" in html
    assert "3" in html
    assert "2" in html
    assert "New Email Ingested" in html


# ── Send (notify_job_ready) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_notify_job_ready_skips_when_disabled():
    with patch("backend.services.email_notification._check_config", return_value="disabled"):
        result = await notify_job_ready("j1", "f.pdf", "Product")
        assert result is False


@pytest.mark.asyncio
async def test_notify_job_ready_success():
    with (
        patch("backend.services.email_notification._check_config", return_value=None),
        patch("backend.services.email_notification._send_smtp", new_callable=AsyncMock) as mock_send,
        patch("backend.services.email_notification._log_notification") as mock_log,
        patch("backend.services.email_notification.settings") as s,
    ):
        s.notification_admin_email = "admin@test.com"
        result = await notify_job_ready("j1", "test.pdf", "Blue Pavé 7")
        assert result is True
        mock_send.assert_awaited_once()
        mock_log.assert_called_once()
        # Verify logged as success
        call_kwargs = mock_log.call_args
        assert call_kwargs[1].get("success", call_kwargs[0][5] if len(call_kwargs[0]) > 5 else None) is True


@pytest.mark.asyncio
async def test_notify_job_ready_smtp_failure():
    with (
        patch("backend.services.email_notification._check_config", return_value=None),
        patch("backend.services.email_notification._send_smtp", new_callable=AsyncMock, side_effect=Exception("SMTP down")),
        patch("backend.services.email_notification._log_notification") as mock_log,
        patch("backend.services.email_notification.settings") as s,
    ):
        s.notification_admin_email = "admin@test.com"
        result = await notify_job_ready("j1", "test.pdf", "Product")
        assert result is False
        mock_log.assert_called_once()
        # Verify logged as failure
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs.get("success") is False
        assert "SMTP down" in call_kwargs.get("error_message", "")


# ── Send (notify_new_email) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_notify_new_email_skips_when_disabled():
    with patch("backend.services.email_notification._check_config", return_value="disabled"):
        result = await notify_new_email("e1", "Subject", "from@x.com", 2, 1)
        assert result is False


@pytest.mark.asyncio
async def test_notify_new_email_success():
    with (
        patch("backend.services.email_notification._check_config", return_value=None),
        patch("backend.services.email_notification._send_smtp", new_callable=AsyncMock) as mock_send,
        patch("backend.services.email_notification._log_notification") as mock_log,
        patch("backend.services.email_notification.settings") as s,
    ):
        s.notification_admin_email = "admin@test.com"
        result = await notify_new_email("e1", "FW: Lab", "lab@x.com", 3, 2)
        assert result is True
        mock_send.assert_awaited_once()
        mock_log.assert_called_once()


# ── Dispatch helpers ──────────────────────────────────────────────


def test_dispatch_job_ready_celery():
    with patch("backend.tasks.notification_tasks.send_job_ready_notification") as mock_task:
        mock_task.delay = MagicMock()
        from backend.tasks.notification_tasks import dispatch_job_ready_notification
        dispatch_job_ready_notification("j1", "f.pdf", "Product")
        mock_task.delay.assert_called_once_with("j1", "f.pdf", "Product")


def test_dispatch_job_ready_thread_fallback():
    with (
        patch("backend.tasks.notification_tasks.send_job_ready_notification") as mock_task,
        patch("backend.tasks.notification_tasks.Thread") as mock_thread,
    ):
        mock_task.delay.side_effect = Exception("Redis down")
        from backend.tasks.notification_tasks import dispatch_job_ready_notification
        dispatch_job_ready_notification("j1", "f.pdf", "Product")
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()


def test_dispatch_new_email_celery():
    with patch("backend.tasks.notification_tasks.send_new_email_notification") as mock_task:
        mock_task.delay = MagicMock()
        from backend.tasks.notification_tasks import dispatch_new_email_notification
        dispatch_new_email_notification("e1", "Subject", "from@x.com", 2, 1)
        mock_task.delay.assert_called_once_with("e1", "Subject", "from@x.com", 2, 1)


def test_dispatch_new_email_thread_fallback():
    with (
        patch("backend.tasks.notification_tasks.send_new_email_notification") as mock_task,
        patch("backend.tasks.notification_tasks.Thread") as mock_thread,
    ):
        mock_task.delay.side_effect = Exception("Redis down")
        from backend.tasks.notification_tasks import dispatch_new_email_notification
        dispatch_new_email_notification("e1", "Sub", "from@x.com", 3, 2)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
