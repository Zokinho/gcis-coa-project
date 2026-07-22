"""Optional API key authentication for service-to-service calls."""

from fastapi import Request, HTTPException


async def verify_api_key(request: Request) -> None:
    """Middleware that checks X-API-Key header if COA_API_KEY is configured.

    - If COA_API_KEY env var is empty/unset, all requests pass through.
    - Cookie-based admin auth still works (browser sessions).
    - API key is required only when no session_token cookie is present.
    """
    from backend.config import settings

    api_key = getattr(settings, "coa_api_key", "")
    if not api_key:
        return  # No API key configured — open access

    # Skip if already authenticated via cookie (browser session)
    if request.cookies.get("session_token"):
        return

    # Check X-API-Key header
    provided_key = request.headers.get("X-API-Key", "")
    if provided_key == api_key:
        return

    # Allow health check without auth
    if request.url.path == "/health":
        return

    raise HTTPException(status_code=401, detail="Invalid or missing API key")
