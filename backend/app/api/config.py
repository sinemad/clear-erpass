"""Config API routes.

Exposes GET/PUT /api/config so the web UI can read and update the
ClearPass connection settings stored in SQLite.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import AppSettings
from app.db.session import get_db
from app.models.config import ConfigRead, ConfigUpdate

router = APIRouter(prefix="/api/config", tags=["config"])

_SETTINGS_ID = 1


def _get_or_create_row(db: Session) -> AppSettings:
    row = db.get(AppSettings, _SETTINGS_ID)
    if row is None:
        row = AppSettings(id=_SETTINGS_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=ConfigRead)
def get_config(db: Annotated[Session, Depends(get_db)]) -> ConfigRead:
    """Return current ClearPass connection config (token value never returned)."""
    row = _get_or_create_row(db)
    return ConfigRead(
        clearpass_base_url=row.clearpass_base_url,
        clearpass_api_token_configured=bool(row.clearpass_api_token),
        clearpass_verify_ssl=row.clearpass_verify_ssl,
    )


@router.put("", response_model=ConfigRead)
def update_config(
    body: ConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ConfigRead:
    """Update ClearPass connection config.

    If `clearpass_api_token` is omitted or empty, the existing token is kept.
    """
    row = _get_or_create_row(db)
    row.clearpass_base_url = body.clearpass_base_url
    row.clearpass_verify_ssl = body.clearpass_verify_ssl
    if body.clearpass_api_token:
        row.clearpass_api_token = body.clearpass_api_token
    db.commit()
    db.refresh(row)
    return ConfigRead(
        clearpass_base_url=row.clearpass_base_url,
        clearpass_api_token_configured=bool(row.clearpass_api_token),
        clearpass_verify_ssl=row.clearpass_verify_ssl,
    )
