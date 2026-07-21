"""SharePoint router — browse sites/drives/folders and upload published PDFs."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_admin_user, get_api_or_admin_user
from backend.config import settings
from backend.database import get_db
from backend.models import CoAJob, JobStatus, Product, SyncLog, SyncTarget
from backend.services.sharepoint import create_folder, list_drives, list_folder_children, list_sites, upload_pdf

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sharepoint"])


class CreateFolderRequest(BaseModel):
    drive_id: str
    parent_folder_id: str
    folder_name: str


class UploadRequest(BaseModel):
    job_id: str
    site_id: str
    drive_id: str
    folder_id: str


class UploadByJobRequest(BaseModel):
    job_id: str


# ── Browse ────────────────────────────────────────────────────────


@router.get("/api/sharepoint/sites")
async def get_sites(_admin: str = Depends(get_admin_user)):
    try:
        return await list_sites()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.exception("Graph API error listing sites")
        raise HTTPException(status_code=502, detail=f"SharePoint error: {exc}")


@router.get("/api/sharepoint/sites/{site_id}/drives")
async def get_drives(site_id: str, _admin: str = Depends(get_admin_user)):
    try:
        return await list_drives(site_id)
    except Exception as exc:
        logger.exception("Graph API error listing drives")
        raise HTTPException(status_code=502, detail=f"SharePoint error: {exc}")


@router.get("/api/sharepoint/sites/{site_id}/drives/{drive_id}/folders")
async def get_folders(
    site_id: str,
    drive_id: str,
    folder_id: str = "root",
    _admin: str = Depends(get_admin_user),
):
    try:
        return await list_folder_children(site_id, drive_id, folder_id)
    except Exception as exc:
        logger.exception("Graph API error listing folders")
        raise HTTPException(status_code=502, detail=f"SharePoint error: {exc}")


@router.post("/api/sharepoint/folders")
async def create_new_folder(
    body: CreateFolderRequest,
    _admin: str = Depends(get_admin_user),
):
    try:
        return await create_folder(body.drive_id, body.parent_folder_id, body.folder_name)
    except Exception as exc:
        logger.exception("Graph API error creating folder")
        raise HTTPException(status_code=502, detail=f"SharePoint error: {exc}")


# ── Upload ────────────────────────────────────────────────────────


@router.post("/api/sharepoint/upload")
async def upload_to_sharepoint(
    body: UploadRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    job = db.query(CoAJob).filter(CoAJob.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.published:
        raise HTTPException(status_code=400, detail="Job must be published before uploading to SharePoint")
    if not job.product_id:
        raise HTTPException(status_code=400, detail="Job has no linked product")

    product = db.query(Product).filter(Product.id == job.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    pub_dir = settings.published_path / product.id
    pdfs = list(pub_dir.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(status_code=404, detail="Published PDF not found on disk")

    pdf_path = pdfs[0]

    try:
        result = await upload_pdf(
            site_id=body.site_id,
            drive_id=body.drive_id,
            folder_id=body.folder_id,
            file_path=pdf_path,
            filename=pdf_path.name,
        )

        sync_log = SyncLog(
            product_id=product.id,
            target=SyncTarget.sharepoint,
            external_id=result.get("id", ""),
            external_url=result.get("web_url", ""),
            extra={"name": result.get("name", "")},
        )
        db.add(sync_log)
        db.commit()

        return result
    except Exception as exc:
        logger.exception("Graph API error uploading PDF")
        raise HTTPException(status_code=502, detail=f"SharePoint upload failed: {exc}")


@router.post("/api/sharepoint/upload-by-job")
async def upload_by_job(
    body: UploadByJobRequest,
    db: Session = Depends(get_db),
    _user: str = Depends(get_api_or_admin_user),
):
    """Upload a published CoA PDF to SharePoint using default destination config.

    Accepts either X-API-Key or session_token cookie for auth.
    Uses SP_DEFAULT_SITE_ID / SP_DEFAULT_DRIVE_ID / SP_DEFAULT_FOLDER_ID.
    """
    if not settings.sp_default_site_id or not settings.sp_default_drive_id or not settings.sp_default_folder_id:
        raise HTTPException(status_code=503, detail="SharePoint default destination not configured")

    job = db.query(CoAJob).filter(CoAJob.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.published:
        raise HTTPException(status_code=400, detail="Job must be published before uploading to SharePoint")
    if not job.product_id:
        raise HTTPException(status_code=400, detail="Job has no linked product")

    product = db.query(Product).filter(Product.id == job.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    pub_dir = settings.published_path / product.id
    pdfs = list(pub_dir.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(status_code=404, detail="Published PDF not found on disk")

    pdf_path = pdfs[0]

    try:
        result = await upload_pdf(
            site_id=settings.sp_default_site_id,
            drive_id=settings.sp_default_drive_id,
            folder_id=settings.sp_default_folder_id,
            file_path=pdf_path,
            filename=pdf_path.name,
        )

        sync_log = SyncLog(
            product_id=product.id,
            target=SyncTarget.sharepoint,
            external_id=result.get("id", ""),
            external_url=result.get("web_url", ""),
            extra={"name": result.get("name", "")},
        )
        db.add(sync_log)
        db.commit()

        return result
    except Exception as exc:
        logger.exception("Graph API error uploading PDF (upload-by-job)")
        raise HTTPException(status_code=502, detail=f"SharePoint upload failed: {exc}")
