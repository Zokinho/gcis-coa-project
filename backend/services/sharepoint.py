"""SharePoint integration via Microsoft Graph API."""

import logging
from pathlib import Path

from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.sites.sites_request_builder import SitesRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration

from backend.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton — reused across requests
_credential: ClientSecretCredential | None = None
_client: GraphServiceClient | None = None


def _get_client() -> GraphServiceClient:
    """Return (or create) the Graph API client singleton."""
    global _credential, _client
    if _client is None:
        if not all([settings.ms_tenant_id, settings.ms_client_id, settings.ms_client_secret]):
            raise RuntimeError("SharePoint credentials not configured (MS_TENANT_ID / MS_CLIENT_ID / MS_CLIENT_SECRET)")
        _credential = ClientSecretCredential(
            settings.ms_tenant_id,
            settings.ms_client_id,
            settings.ms_client_secret,
        )
        _client = GraphServiceClient(
            credentials=_credential,
            scopes=["https://graph.microsoft.com/.default"],
        )
    return _client


async def list_sites() -> list[dict]:
    """Return all SharePoint sites visible to the app."""
    client = _get_client()
    result = await client.sites.get_all_sites.get()

    sites: list[dict] = []
    if result and result.value:
        for s in result.value:
            sites.append({
                "id": s.id,
                "name": s.display_name or s.name or "",
                "web_url": s.web_url or "",
            })
    return sites


async def list_drives(site_id: str) -> list[dict]:
    """Return document libraries (drives) for a site."""
    client = _get_client()
    result = await client.sites.by_site_id(site_id).drives.get()

    drives: list[dict] = []
    if result and result.value:
        for d in result.value:
            drives.append({
                "id": d.id,
                "name": d.name or "",
            })
    return drives


async def list_folder_children(site_id: str, drive_id: str, folder_id: str = "root") -> list[dict]:
    """Return child *folders* (not files) for a given folder."""
    client = _get_client()
    result = await client.drives.by_drive_id(drive_id).items.by_drive_item_id(folder_id).children.get()

    folders: list[dict] = []
    if result and result.value:
        for item in result.value:
            if item.folder is not None:
                folders.append({
                    "id": item.id,
                    "name": item.name or "",
                })
    return folders


async def create_folder(drive_id: str, parent_folder_id: str, folder_name: str) -> dict:
    """Create a new subfolder. Returns {id, name}."""
    client = _get_client()
    from msgraph.generated.models.drive_item import DriveItem
    from msgraph.generated.models.folder import Folder

    new_folder = DriveItem()
    new_folder.name = folder_name
    new_folder.folder = Folder()

    result = await client.drives.by_drive_id(drive_id).items.by_drive_item_id(parent_folder_id).children.post(new_folder)

    return {
        "id": getattr(result, "id", ""),
        "name": getattr(result, "name", folder_name),
    }


async def upload_pdf(site_id: str, drive_id: str, folder_id: str, file_path: Path, filename: str) -> dict:
    """Upload a PDF to a SharePoint folder. Returns {id, name, web_url}."""
    client = _get_client()

    with open(file_path, "rb") as f:
        content = f.read()

    # Upload via PUT to {folder_id}:/{filename}:/content
    item_path = f"{folder_id}:/{filename}:"
    result = await client.drives.by_drive_id(drive_id).items.by_drive_item_id(item_path).content.put(content)

    return {
        "id": getattr(result, "id", ""),
        "name": getattr(result, "name", filename),
        "web_url": getattr(result, "web_url", ""),
    }
