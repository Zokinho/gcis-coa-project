"""Tests for PDF unlock service."""

from pathlib import Path
from unittest.mock import patch

import pikepdf
import pytest

from backend.services.pdf_unlock import unlock_pdf


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a simple unencrypted PDF for testing."""
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    path = tmp_path / "test.pdf"
    pdf.save(path)
    return path


@pytest.fixture
def owner_locked_pdf(tmp_path: Path) -> Path:
    """Create a PDF with an owner password (but no user password)."""
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    path = tmp_path / "owner_locked.pdf"
    pdf.save(
        path,
        encryption=pikepdf.Encryption(owner="secret123", user=""),
    )
    return path


@pytest.fixture
def user_locked_pdf(tmp_path: Path) -> Path:
    """Create a PDF with a user password."""
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    path = tmp_path / "user_locked.pdf"
    pdf.save(
        path,
        encryption=pikepdf.Encryption(owner="owner123", user="user123"),
    )
    return path


def test_unlock_unencrypted_pdf(sample_pdf: Path, tmp_path: Path):
    output = tmp_path / "output.pdf"
    success, was_locked, error = unlock_pdf(sample_pdf, output)
    assert success is True
    assert was_locked is False
    assert error is None
    assert output.exists()


def test_unlock_owner_password_pdf(owner_locked_pdf: Path, tmp_path: Path):
    output = tmp_path / "output.pdf"
    success, was_locked, error = unlock_pdf(owner_locked_pdf, output)
    assert success is True
    assert was_locked is True
    assert error is None
    assert output.exists()
    # Verify the output is not encrypted
    pdf = pikepdf.open(output)
    assert not pdf.is_encrypted
    pdf.close()


def test_unlock_user_password_pdf(user_locked_pdf: Path, tmp_path: Path):
    output = tmp_path / "output.pdf"
    success, was_locked, error = unlock_pdf(user_locked_pdf, output)
    assert success is False
    assert was_locked is True
    assert "user-password" in error.lower()


def test_unlock_nonexistent_file(tmp_path: Path):
    output = tmp_path / "output.pdf"
    success, was_locked, error = unlock_pdf(tmp_path / "nope.pdf", output)
    assert success is False
    assert error is not None


def test_unlock_rejects_non_pdf_file(tmp_path: Path):
    """A file with .pdf extension but non-PDF content should be rejected."""
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_text("This is not a PDF file at all.")
    output = tmp_path / "output.pdf"
    success, was_locked, error = unlock_pdf(fake_pdf, output)
    assert success is False
    assert was_locked is False
    assert "bad magic bytes" in error.lower()
    assert not output.exists()


def test_unlock_rejects_too_many_pages(tmp_path: Path):
    """A PDF exceeding the page count limit should be rejected."""
    pdf = pikepdf.Pdf.new()
    for _ in range(6):
        pdf.add_blank_page(page_size=(612, 792))
    path = tmp_path / "big.pdf"
    pdf.save(path)

    output = tmp_path / "output.pdf"
    with patch("backend.services.pdf_unlock.settings") as mock_settings:
        mock_settings.max_pdf_page_count = 5
        success, was_locked, error = unlock_pdf(path, output)
    assert success is False
    assert was_locked is False
    assert "6 pages" in error
    assert "limit of 5" in error


def test_unlock_real_coa():
    """Test with the real Eurofins CoA if available."""
    coa_path = Path(__file__).parent.parent.parent / "test_data" / "BP_T-003-23_COA__Eurofins_.pdf"
    if not coa_path.exists():
        pytest.skip("Test CoA not found")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "unlocked.pdf"
        success, was_locked, error = unlock_pdf(coa_path, output)
        assert success is True
        assert error is None
        assert output.exists()
