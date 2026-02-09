"""Access token router — manage buyer access tokens."""

import logging
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_admin_user
from backend.database import get_db
from backend.models import (
    AccessToken,
    AccessTokenCreate,
    AccessTokenResponse,
    AccessTokenUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/access", tags=["access"])


@router.post("/tokens", response_model=AccessTokenResponse)
def create_token(
    body: AccessTokenCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    token = AccessToken(
        token=secrets.token_urlsafe(32),
        label=body.label,
        tiers=body.tiers,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@router.get("/tokens", response_model=list[AccessTokenResponse])
def list_tokens(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    return db.query(AccessToken).order_by(AccessToken.created_at.desc()).all()


@router.patch("/tokens/{token_id}", response_model=AccessTokenResponse)
def update_token(
    token_id: str,
    body: AccessTokenUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    token = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    if body.label is not None:
        token.label = body.label
    if body.tiers is not None:
        token.tiers = body.tiers
    if body.active is not None:
        token.active = body.active

    db.commit()
    db.refresh(token)
    return token


@router.delete("/tokens/{token_id}")
def delete_token(
    token_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_user),
):
    token = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.active = False
    db.commit()
    return {"ok": True}


@router.get("/validate/{token}")
def validate_token(token: str, db: Session = Depends(get_db)):
    """Public endpoint — validates a buyer token and returns allowed tiers."""
    access_token = db.query(AccessToken).filter(
        AccessToken.token == token,
        AccessToken.active == True,
    ).first()
    if not access_token:
        raise HTTPException(status_code=404, detail="Invalid or inactive token")

    access_token.last_used = datetime.utcnow()
    access_token.use_count += 1
    db.commit()
    return {"valid": True, "label": access_token.label, "tiers": access_token.tiers}
