"""Evernote import — pull existing notes (PDFs + photos) into GCIS."""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import (
    CoAJob,
    EvernoteImport,
    EvernoteImportStatus,
    ProductPhoto,
)
from backend.tasks.dispatch import send_process_coa

logger = logging.getLogger(__name__)

# NOTE: evernote_service imports (_get_note_store, _reset_note_store)
# are lazy-loaded inside each function to avoid import errors when
# evernote3 SDK is not installed or credentials are not configured.

# MIME types we care about
PDF_MIMES = {"application/pdf"}
IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# ── Mock mode: activated when EVERNOTE_DEVELOPER_TOKEN is not set ──────────

_MOCK_ENABLED = not settings.evernote_developer_token

_MOCK_NOTES = [
    {
        "guid": "mock-note-001",
        "title": "Culture des Sommets — CoA Records",
        "updated": datetime(2025, 12, 15, 14, 30).isoformat(),
        "resource_count": 3,
        "resources": [
            {"guid": "mock-res-001a", "filename": "BP_T-003-23_COA__Eurofins_.pdf",
             "mime": "application/pdf", "size": 2053261, "is_pdf": True, "is_image": False},
            {"guid": "mock-res-001b", "filename": "flower_photo_1.jpg",
             "mime": "image/jpeg", "size": 245000, "is_pdf": False, "is_image": True},
            {"guid": "mock-res-001c", "filename": "flower_photo_2.jpg",
             "mime": "image/jpeg", "size": 198000, "is_pdf": False, "is_image": True},
        ],
    },
    {
        "guid": "mock-note-002",
        "title": "Green Valley Farms — CoA Records",
        "updated": datetime(2025, 11, 22, 9, 15).isoformat(),
        "resource_count": 2,
        "resources": [
            {"guid": "mock-res-002a", "filename": "GVF_Potency_Report.pdf",
             "mime": "application/pdf", "size": 1850000, "is_pdf": True, "is_image": False},
            {"guid": "mock-res-002b", "filename": "product_label.png",
             "mime": "image/png", "size": 312000, "is_pdf": False, "is_image": True},
        ],
    },
    {
        "guid": "mock-note-003",
        "title": "Mountain Peak Cannabis — CoA Records",
        "updated": datetime(2025, 10, 5, 16, 45).isoformat(),
        "resource_count": 1,
        "resources": [
            {"guid": "mock-res-003a", "filename": "MPC_Full_Panel_2025.pdf",
             "mime": "application/pdf", "size": 2200000, "is_pdf": True, "is_image": False},
        ],
    },
]

# Path to test PDF used by mock import
_MOCK_PDF_SOURCE = Path("test_data/BP_T-003-23_COA__Eurofins_.pdf")


def _mock_list_notes(db: Session) -> list[dict]:
    """Return fake Evernote notes for demo/testing."""
    imported_guids = {g for (g,) in db.query(EvernoteImport.note_guid).all()}
    return [
        {
            "guid": n["guid"],
            "title": n["title"],
            "updated": n["updated"],
            "resource_count": n["resource_count"],
            "already_imported": n["guid"] in imported_guids,
        }
        for n in _MOCK_NOTES
    ]


def _mock_preview_note(note_guid: str) -> dict:
    """Return fake note preview for demo/testing."""
    note = next((n for n in _MOCK_NOTES if n["guid"] == note_guid), None)
    if not note:
        raise ValueError(f"Mock note not found: {note_guid}")
    client_name = _parse_client_name_from_title(note["title"])
    pdf_count = sum(1 for r in note["resources"] if r["is_pdf"])
    photo_count = sum(1 for r in note["resources"] if r["is_image"])
    return {
        "guid": note_guid,
        "title": note["title"],
        "client_name": client_name,
        "resources": note["resources"],
        "pdf_count": pdf_count,
        "photo_count": photo_count,
    }


def _mock_import_note(note_guid: str, client_name_override: str | None = None) -> str:
    """Import using the real test PDF for demo. Triggers actual pipeline."""
    note = next((n for n in _MOCK_NOTES if n["guid"] == note_guid), None)
    if not note:
        raise ValueError(f"Mock note not found: {note_guid}")

    db: Session = SessionLocal()
    try:
        title = note["title"]
        client_name = client_name_override or _parse_client_name_from_title(title)

        # Reuse existing pending record if one was created by the router
        imp = db.query(EvernoteImport).filter(
            EvernoteImport.note_guid == note_guid,
            EvernoteImport.status == EvernoteImportStatus.pending,
        ).order_by(EvernoteImport.created_at.desc()).first()

        if imp:
            imp.status = EvernoteImportStatus.processing
            imp.note_title = title
            imp.client_name = client_name
            db.commit()
        else:
            imp = EvernoteImport(
                note_guid=note_guid,
                note_title=title,
                client_name=client_name,
                status=EvernoteImportStatus.processing,
            )
            db.add(imp)
            db.commit()
            db.refresh(imp)

        import_id = imp.id

        pdfs_found = 0
        photos_found = 0
        pdfs_imported = 0
        photos_imported = 0

        for res in note["resources"]:
            if res["is_pdf"]:
                pdfs_found += 1
                # Copy real test PDF into uploads
                if _MOCK_PDF_SOURCE.exists():
                    safe_fn = f"evernote_{res['guid'][:8]}.pdf"
                    dest = settings.uploads_path / safe_fn
                    if dest.exists():
                        safe_fn = f"{import_id[:8]}_{safe_fn}"
                        dest = settings.uploads_path / safe_fn
                    shutil.copy2(_MOCK_PDF_SOURCE, dest)

                    job = CoAJob(
                        filename=safe_fn,
                        client_name=client_name,
                        evernote_import_id=import_id,
                    )
                    db.add(job)
                    db.commit()
                    db.refresh(job)
                    send_process_coa(job.id)
                    pdfs_imported += 1
                else:
                    logger.warning("Mock PDF source not found: %s", _MOCK_PDF_SOURCE)

            elif res["is_image"]:
                photos_found += 1
                # Create a small placeholder image
                import_dir = settings.evernote_imports_path / import_id
                import_dir.mkdir(parents=True, exist_ok=True)
                placeholder = import_dir / res["filename"]
                # Write a minimal 1x1 JPEG placeholder
                placeholder.write_bytes(
                    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
                    b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
                    b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
                    b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
                    b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
                    b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00'
                    b'\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
                    b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa7\xa3\xff\xd9'
                )
                photo = ProductPhoto(
                    product_id="",
                    original_filename=res["filename"],
                    stored_filename=str(placeholder),
                    mime_type=res["mime"],
                    file_size=len(placeholder.read_bytes()),
                    source="evernote",
                    source_id=res["guid"],
                )
                db.add(photo)
                photos_imported += 1

        imp.pdfs_found = pdfs_found
        imp.photos_found = photos_found
        imp.pdfs_imported = pdfs_imported
        imp.photos_imported = photos_imported
        imp.status = EvernoteImportStatus.completed
        db.commit()

        logger.info(
            "Mock Evernote import %s completed: %d PDFs, %d photos from note '%s'",
            import_id, pdfs_imported, photos_imported, title,
        )
        return import_id

    except Exception as e:
        logger.exception("Mock Evernote import failed for note %s", note_guid)
        try:
            imp = db.query(EvernoteImport).filter(
                EvernoteImport.note_guid == note_guid
            ).order_by(EvernoteImport.created_at.desc()).first()
            if imp and imp.status == EvernoteImportStatus.processing:
                imp.status = EvernoteImportStatus.error
                imp.error_message = str(e)
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


# ── End mock mode ─────────────────────────────────────────────────────────


def _parse_client_name_from_title(title: str) -> str:
    """Extract client name from note title like 'ClientName — CoA Records'."""
    # Try splitting on em-dash, en-dash, or double hyphen
    for sep in [" — ", " – ", " -- ", " - "]:
        if sep in title:
            return title.split(sep)[0].strip()
    return title.strip()


def list_evernote_notes(db: Session) -> list[dict]:
    """List notes from the configured Evernote notebook with import status."""
    if _MOCK_ENABLED:
        return _mock_list_notes(db)

    from backend.services.evernote_service import _get_note_store, _reset_note_store

    try:
        note_store = _get_note_store()
    except Exception:
        _reset_note_store()
        raise

    from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec

    note_filter = NoteFilter()
    if settings.evernote_notebook_guid:
        note_filter.notebookGuid = settings.evernote_notebook_guid

    spec = NotesMetadataResultSpec()
    spec.includeTitle = True
    spec.includeUpdated = True
    spec.includeAttributes = True

    try:
        results = note_store.findNotesMetadata(note_filter, 0, 250, spec)
    except Exception:
        _reset_note_store()
        raise

    # Check which notes have already been imported
    imported_guids = set()
    existing = db.query(EvernoteImport.note_guid).all()
    for (guid,) in existing:
        imported_guids.add(guid)

    notes = []
    for meta in results.notes:
        updated = None
        if meta.updated:
            updated = datetime.utcfromtimestamp(meta.updated / 1000).isoformat()

        # Count resources from the note itself (need full note for accurate count)
        resource_count = 0
        try:
            note = note_store.getNote(meta.guid, False, False, False, False)
            resource_count = len(note.resources) if note.resources else 0
        except Exception:
            pass

        notes.append({
            "guid": meta.guid,
            "title": meta.title or "",
            "updated": updated,
            "resource_count": resource_count,
            "already_imported": meta.guid in imported_guids,
        })

    return notes


def preview_evernote_note(note_guid: str) -> dict:
    """Preview a note's resources (PDFs and images) for import."""
    if _MOCK_ENABLED:
        return _mock_preview_note(note_guid)

    from backend.services.evernote_service import _get_note_store, _reset_note_store

    try:
        note_store = _get_note_store()
        note = note_store.getNote(note_guid, True, False, False, False)
    except Exception:
        _reset_note_store()
        raise

    title = note.title or ""
    client_name = _parse_client_name_from_title(title)

    resources = []
    pdf_count = 0
    photo_count = 0

    if note.resources:
        for res in note.resources:
            mime = res.mime or ""
            filename = ""
            if res.attributes and res.attributes.fileName:
                filename = res.attributes.fileName
            size = res.data.size if res.data else 0

            is_pdf = mime in PDF_MIMES
            is_image = mime in IMAGE_MIMES

            if is_pdf:
                pdf_count += 1
            if is_image:
                photo_count += 1

            if is_pdf or is_image:
                resources.append({
                    "guid": res.guid,
                    "filename": filename or f"resource_{res.guid[:8]}.{'pdf' if is_pdf else 'jpg'}",
                    "mime": mime,
                    "size": size,
                    "is_pdf": is_pdf,
                    "is_image": is_image,
                })

    return {
        "guid": note_guid,
        "title": title,
        "client_name": client_name,
        "resources": resources,
        "pdf_count": pdf_count,
        "photo_count": photo_count,
    }


def import_evernote_note(note_guid: str, client_name_override: str | None = None) -> str:
    """Import PDFs and photos from an Evernote note. Returns the import record ID."""
    if _MOCK_ENABLED:
        return _mock_import_note(note_guid, client_name_override)

    from backend.services.evernote_service import _get_note_store, _reset_note_store

    db: Session = SessionLocal()
    try:
        note_store = _get_note_store()
        note = note_store.getNote(note_guid, True, False, False, False)

        title = note.title or ""
        client_name = client_name_override or _parse_client_name_from_title(title)

        # Reuse existing pending record if one was created by the router
        imp = db.query(EvernoteImport).filter(
            EvernoteImport.note_guid == note_guid,
            EvernoteImport.status == EvernoteImportStatus.pending,
        ).order_by(EvernoteImport.created_at.desc()).first()

        if imp:
            imp.status = EvernoteImportStatus.processing
            imp.note_title = title
            imp.client_name = client_name
            db.commit()
        else:
            imp = EvernoteImport(
                note_guid=note_guid,
                note_title=title,
                client_name=client_name,
                status=EvernoteImportStatus.processing,
            )
            db.add(imp)
            db.commit()
            db.refresh(imp)

        import_id = imp.id
        pdfs_found = 0
        photos_found = 0
        pdfs_imported = 0
        photos_imported = 0

        if note.resources:
            for res in note.resources:
                mime = res.mime or ""
                is_pdf = mime in PDF_MIMES
                is_image = mime in IMAGE_MIMES

                if not (is_pdf or is_image):
                    continue

                if is_pdf:
                    pdfs_found += 1
                if is_image:
                    photos_found += 1

                # Download resource data
                try:
                    res_data = note_store.getResourceData(res.guid)
                except Exception:
                    logger.exception("Failed to download resource %s", res.guid)
                    continue

                filename = ""
                if res.attributes and res.attributes.fileName:
                    filename = res.attributes.fileName

                if is_pdf:
                    # Save PDF and create CoAJob
                    if not filename:
                        filename = f"evernote_{res.guid[:8]}.pdf"
                    # Sanitize filename
                    safe_filename = re.sub(r'[^\w\-.]', '_', filename)
                    upload_path = settings.uploads_path / safe_filename

                    # Avoid overwrites
                    if upload_path.exists():
                        safe_filename = f"{imp.id[:8]}_{safe_filename}"
                        upload_path = settings.uploads_path / safe_filename

                    with open(upload_path, "wb") as f:
                        f.write(res_data)

                    job = CoAJob(
                        filename=safe_filename,
                        client_name=client_name,
                        evernote_import_id=import_id,
                    )
                    db.add(job)
                    db.commit()
                    db.refresh(job)

                    # Dispatch processing
                    send_process_coa(job.id)
                    pdfs_imported += 1

                elif is_image:
                    # Save photo to evernote_imports directory
                    if not filename:
                        ext = "jpg" if "jpeg" in mime else mime.split("/")[-1]
                        filename = f"evernote_{res.guid[:8]}.{ext}"

                    safe_filename = re.sub(r'[^\w\-.]', '_', filename)
                    import_dir = settings.evernote_imports_path / import_id
                    import_dir.mkdir(parents=True, exist_ok=True)
                    photo_path = import_dir / safe_filename

                    with open(photo_path, "wb") as f:
                        f.write(res_data)

                    # Create ProductPhoto record (product_id will be linked later
                    # when the PDF jobs complete and products are created)
                    photo = ProductPhoto(
                        product_id="",  # Will be linked when products are created
                        original_filename=filename,
                        stored_filename=str(photo_path),
                        mime_type=mime,
                        file_size=len(res_data),
                        source="evernote",
                        source_id=res.guid,
                    )
                    db.add(photo)
                    photos_imported += 1

        # Update import record
        imp.pdfs_found = pdfs_found
        imp.photos_found = photos_found
        imp.pdfs_imported = pdfs_imported
        imp.photos_imported = photos_imported
        imp.status = EvernoteImportStatus.completed
        db.commit()

        logger.info(
            "Evernote import %s completed: %d PDFs, %d photos from note '%s'",
            import_id, pdfs_imported, photos_imported, title,
        )
        return import_id

    except Exception as e:
        logger.exception("Evernote import failed for note %s", note_guid)
        try:
            imp = db.query(EvernoteImport).filter(EvernoteImport.note_guid == note_guid).order_by(EvernoteImport.created_at.desc()).first()
            if imp and imp.status == EvernoteImportStatus.processing:
                imp.status = EvernoteImportStatus.error
                imp.error_message = str(e)
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
