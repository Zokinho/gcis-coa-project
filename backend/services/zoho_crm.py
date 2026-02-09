"""Zoho CRM integration — create Products and attach PDFs via REST API v8."""

import logging
import time
from pathlib import Path

import httpx

from backend.config import settings
from backend.models import Product, ProductTestData

logger = logging.getLogger(__name__)

# ── Data center URL map ──────────────────────────────────────────

_DC_MAP: dict[str, tuple[str, str]] = {
    "US": ("accounts.zoho.com", "zohoapis.com"),
    "CA": ("accounts.zohocloud.ca", "zohoapis.ca"),
    "EU": ("accounts.zoho.eu", "zohoapis.eu"),
}

# ── Token cache ──────────────────────────────────────────────────

_access_token: str | None = None
_token_expires_at: float = 0.0


def _dc_hosts() -> tuple[str, str]:
    dc = settings.zoho_data_center.upper()
    if dc not in _DC_MAP:
        raise ValueError(f"Unknown Zoho data center: {dc!r}  (expected US, CA, or EU)")
    return _DC_MAP[dc]


async def _get_token() -> str:
    """Return a valid access token, refreshing if expired."""
    global _access_token, _token_expires_at

    if _access_token and time.time() < _token_expires_at:
        return _access_token

    if not all([settings.zoho_client_id, settings.zoho_client_secret, settings.zoho_refresh_token]):
        raise RuntimeError("Zoho CRM credentials not configured (ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET / ZOHO_REFRESH_TOKEN)")

    accounts_host, _ = _dc_hosts()
    url = f"https://{accounts_host}/oauth/v2/token"
    params = {
        "grant_type": "refresh_token",
        "client_id": settings.zoho_client_id,
        "client_secret": settings.zoho_client_secret,
        "refresh_token": settings.zoho_refresh_token,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    if "access_token" not in data:
        raise RuntimeError(f"Zoho token refresh failed: {data}")

    _access_token = data["access_token"]
    # Tokens last 3600s; refresh 60s early
    _token_expires_at = time.time() + data.get("expires_in", 3600) - 60
    logger.info("Zoho CRM access token refreshed")
    return _access_token


def _api_base() -> str:
    _, api_host = _dc_hosts()
    return f"https://{api_host}/crm/v8"


def _record_url(record_id: str) -> str:
    _, api_host = _dc_hosts()
    # CRM UI is on the same domain root as the API host
    base = api_host.replace("zohoapis", "crm.zohocloud") if "zohocloud" in api_host else api_host.replace("zohoapis", "crm.zoho")
    return f"https://{base}/crm/tab/Products/{record_id}"


# ── API calls ────────────────────────────────────────────────────


async def create_product(product_data: dict) -> dict:
    """Create a Product record in Zoho CRM. Returns {id, created_time}."""
    token = await _get_token()
    url = f"{_api_base()}/Products"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Zoho-oauthtoken {token}"},
            json={"data": [product_data]},
        )
        resp.raise_for_status()
        body = resp.json()

    details = body.get("data", [{}])[0]
    if details.get("code") != "SUCCESS":
        raise RuntimeError(f"Zoho CRM create failed: {details}")

    return {
        "id": details["details"]["id"],
        "created_time": details["details"].get("Created_Time", ""),
    }


async def upload_attachment(record_id: str, file_path: Path, filename: str) -> dict:
    """Attach a file to a Products record. Returns {id}."""
    token = await _get_token()
    url = f"{_api_base()}/Products/{record_id}/Attachments"

    with open(file_path, "rb") as f:
        file_content = f.read()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Zoho-oauthtoken {token}"},
            files={"file": (filename, file_content, "application/pdf")},
        )
        resp.raise_for_status()
        body = resp.json()

    details = body.get("data", [{}])[0]
    if details.get("code") != "SUCCESS":
        raise RuntimeError(f"Zoho CRM attachment failed: {details}")

    return {"id": details["details"]["id"]}


# ── Field mapping ────────────────────────────────────────────────


def build_field_mapping(product: Product, test_data: list[ProductTestData]) -> dict:
    """Build the Zoho CRM field dict from our Product + test data."""
    fields: dict = {
        "Product_Name": product.name,
        "Product_Code": product.lot_number,
        "Lab": product.lab,
        "Manufacturer": product.producer or "",
        "Strain_Type": product.strain_type or "",
        "Description": f"[{product.tier}] {product.name}",
    }

    if product.test_date:
        fields["Test_Date"] = product.test_date.isoformat()

    # Extract potency
    for td in test_data:
        if td.test_type == "potency" and td.data:
            results = td.data.get("results", {})
            for key, value in results.items():
                k_lower = key.lower()
                if "thc" in k_lower and "total" in k_lower:
                    fields["THC_Percentage"] = value.get("value") if isinstance(value, dict) else value
                elif "cbd" in k_lower and "total" in k_lower:
                    fields["CBD_Percentage"] = value.get("value") if isinstance(value, dict) else value

    # Extract top terpenes
    for td in test_data:
        if td.test_type == "terpenes" and td.data:
            results = td.data.get("results", {})
            # Sort by value descending, take top 5
            sorted_terps = sorted(
                ((k, v.get("value", 0) if isinstance(v, dict) else v) for k, v in results.items()),
                key=lambda x: float(x[1]) if x[1] else 0,
                reverse=True,
            )
            top = [name for name, _ in sorted_terps[:5]]
            if top:
                fields["Terpene_Profile"] = ", ".join(top)

    return fields


# ── Orchestrator ─────────────────────────────────────────────────


async def push_product_with_pdf(product: Product, test_data: list[ProductTestData], pdf_path: Path) -> dict:
    """Create product record in Zoho CRM and attach the PDF.

    Returns {record_id, record_url}.
    """
    fields = build_field_mapping(product, test_data)
    logger.info("Creating Zoho CRM product: %s", fields.get("Product_Name"))

    result = await create_product(fields)
    record_id = result["id"]
    logger.info("Zoho CRM product created: %s", record_id)

    await upload_attachment(record_id, pdf_path, pdf_path.name)
    logger.info("PDF attached to Zoho CRM record %s", record_id)

    return {
        "record_id": record_id,
        "record_url": _record_url(record_id),
    }
