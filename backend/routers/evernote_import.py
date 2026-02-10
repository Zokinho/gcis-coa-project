"""Evernote import router — browse, preview, and import notes into GCIS."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_admin_user
from backend.database import get_db
from backend.models import (
    EvernoteImport,
    EvernoteImportRequest,
    EvernoteImportResponse,
    EvernoteNoteListItem,
    EvernoteNotePreview,
    EvernoteNoteResource,
)
from backend.services.evernote_import import list_evernote_notes, preview_evernote_note
from backend.tasks.evernote_tasks import dispatch_evernote_import

logger = logging.getLogger(__name__)
router = APIRouter(tags=["evernote-import"])


@router.get("/api/evernote/notes", response_model=list[EvernoteNoteListItem])
async def get_evernote_notes(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """List notes from configured Evernote notebook."""
    try:
        notes = list_evernote_notes(db)
        return [EvernoteNoteListItem(**n) for n in notes]
    except Exception as exc:
        logger.exception("Failed to list Evernote notes")
        raise HTTPException(status_code=502, detail=f"Evernote error: {exc}")


@router.get("/api/evernote/notes/{guid}", response_model=EvernoteNotePreview)
async def get_evernote_note_preview(
    guid: str,
    _admin: str = Depends(get_admin_user),
):
    """Preview a specific Evernote note's resources for import."""
    try:
        data = preview_evernote_note(guid)
        return EvernoteNotePreview(
            guid=data["guid"],
            title=data["title"],
            client_name=data["client_name"],
            resources=[EvernoteNoteResource(**r) for r in data["resources"]],
            pdf_count=data["pdf_count"],
            photo_count=data["photo_count"],
        )
    except Exception as exc:
        logger.exception("Failed to preview Evernote note %s", guid)
        raise HTTPException(status_code=502, detail=f"Evernote error: {exc}")


@router.post("/api/evernote/import", response_model=EvernoteImportResponse)
async def trigger_evernote_import(
    body: EvernoteImportRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Start importing PDFs and photos from an Evernote note."""
    # Create a pending record first so we can return it immediately
    imp = EvernoteImport(
        note_guid=body.note_guid,
        client_name=body.client_name or "",
    )
    db.add(imp)
    db.commit()
    db.refresh(imp)

    # Dispatch async import
    dispatch_evernote_import(body.note_guid, body.client_name)

    return imp


@router.get("/api/evernote/imports", response_model=list[EvernoteImportResponse])
async def list_imports(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """List all Evernote import records."""
    imports = (
        db.query(EvernoteImport)
        .order_by(EvernoteImport.created_at.desc())
        .all()
    )
    return imports


@router.get("/api/evernote/imports/{import_id}", response_model=EvernoteImportResponse)
async def get_import(
    import_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    """Get a specific Evernote import record."""
    imp = db.query(EvernoteImport).filter(EvernoteImport.id == import_id).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Import record not found")
    return imp
