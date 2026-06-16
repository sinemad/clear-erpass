"""Config API routes.

Exposes GET/PUT /api/config so the web UI can read and update the
ClearPass connection settings stored in SQLite.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.logging_config import set_log_level
from app.db.models import AppSettings
from app.db.session import get_db
from app.models.config import ConfigRead, ConfigUpdate

logger = logging.getLogger("app.api.config")
router = APIRouter(prefix="/api/config", tags=["config"])

_SETTINGS_ID = 1


def _get_or_create_row(db: Session) -> AppSettings:
    row = db.get(AppSettings, _SETTINGS_ID)
    if row is None:
        logger.debug("No config row found, creating default")
        row = AppSettings(id=_SETTINGS_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _row_to_read(row: AppSettings) -> ConfigRead:
    return ConfigRead(
        clearpass_base_url=row.clearpass_base_url,
        clearpass_client_id=row.clearpass_client_id,
        clearpass_client_secret_configured=bool(row.clearpass_client_secret),
        clearpass_verify_ssl=row.clearpass_verify_ssl,
        debug_logging=row.debug_logging,
    )


@router.get("", response_model=ConfigRead)
def get_config(db: Annotated[Session, Depends(get_db)]) -> ConfigRead:
    """Return current ClearPass connection config (client secret never returned)."""
    row = _get_or_create_row(db)
    logger.debug(
        "Config read (url=%s, client_id=%s, secret_configured=%s)",
        row.clearpass_base_url,
        row.clearpass_client_id,
        bool(row.clearpass_client_secret),
    )
    return _row_to_read(row)


@router.put("", response_model=ConfigRead)
def update_config(
    body: ConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ConfigRead:
    """Update ClearPass connection config.

    If `clearpass_client_secret` is omitted or empty, the existing secret is kept.
    Changing the URL or client ID invalidates the cached access token.
    """
    row = _get_or_create_row(db)
    secret_changed = bool(body.clearpass_client_secret)
    credentials_changed = (
        body.clearpass_base_url != row.clearpass_base_url
        or body.clearpass_client_id != row.clearpass_client_id
        or secret_changed
    )

    row.clearpass_base_url = body.clearpass_base_url
    row.clearpass_client_id = body.clearpass_client_id
    row.clearpass_verify_ssl = body.clearpass_verify_ssl
    row.debug_logging = body.debug_logging
    if body.clearpass_client_secret:
        row.clearpass_client_secret = body.clearpass_client_secret

    # Invalidate cached token whenever credentials change so it's re-fetched fresh
    if credentials_changed:
        row.clearpass_api_token = None
        row.clearpass_token_expires_at = None

    db.commit()
    db.refresh(row)
    set_log_level("DEBUG" if row.debug_logging else "INFO")
    logger.info(
        "Config updated (url=%s, client_id=%s, secret_changed=%s, debug_logging=%s)",
        row.clearpass_base_url,
        row.clearpass_client_id,
        secret_changed,
        row.debug_logging,
    )
    return _row_to_read(row)
