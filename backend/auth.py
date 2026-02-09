"""JWT-based admin authentication."""

from datetime import datetime, timedelta

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt

from backend.config import settings

ALGORITHM = "HS256"


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.admin_token_expire_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.admin_secret_key, algorithm=ALGORITHM)


def verify_credentials(username: str, password: str) -> bool:
    return username == settings.admin_user and password == settings.admin_password


def get_admin_user(session_token: str | None = Cookie(None)) -> str:
    """FastAPI dependency — validates JWT from cookie, returns username."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = jwt.decode(session_token, settings.admin_secret_key, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
