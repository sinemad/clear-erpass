"""
ClearPass client wrapper.

This module isolates all direct `pyclearpass` usage behind a small wrapper
class (`ClearPassClient`). The rest of the application (API routes, decision
tree builder) should depend on this wrapper and on the Pydantic models in
`backend/app/models/`, NOT on raw `pyclearpass` objects or raw JSON dicts.

Why a wrapper:
- `pyclearpass` exposes the full ClearPass REST API surface (read AND write).
  Wrapping it lets us expose only the read-only methods this project needs
  and enforces the "read-only" constraint in code, not just in docs.
- Keeps token/auth handling and pagination in one place.
- Makes it possible to swap/mock the ClearPass backend in tests without
  touching route or business logic.

IMPORTANT - verify against your installed pyclearpass version:
The exact class/method names for Access Tracker / Insight queries vary
between pyclearpass versions. As of writing, Access Tracker / session log
data is exposed via the Insight API category (commonly something like
`ApiInsight` or `ApiAccessTracker` depending on version -- run
`python -c "from pyclearpass import *; help(ApiInsight)"` or check
`dir(pyclearpass)` against your installed version and adjust the TODOs below
accordingly).
"""

from __future__ import annotations

import logging
import time
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from pyclearpass import ApiLogs, ApiPolicyElements
from sqlalchemy.orm import Session

from app.db.models import AppSettings
from app.db.session import get_db

logger = logging.getLogger("app.clearpass")


class ClearPassClient:
    """Read-only wrapper around the ClearPass Policy Manager REST API.

    Only GET-equivalent operations should be added here. Do not add
    create/update/delete methods -- this project is read-only by design
    (see CLAUDE.md).
    """

    def __init__(self, base_url: str, api_token: str, verify_ssl: bool = True) -> None:
        logger.debug("Initializing ClearPass client for %s (verify_ssl=%s)", base_url, verify_ssl)
        kwargs = dict(server=base_url, api_token=api_token, verify_ssl=verify_ssl)
        self._policy = ApiPolicyElements(**kwargs)
        self._logs = ApiLogs(**kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _check_error(resp: Any, context: str = "") -> None:
        """Raise RuntimeError if pyclearpass returned an API-level error dict."""
        if not isinstance(resp, dict):
            raise RuntimeError(f"Unexpected ClearPass response{f' ({context})' if context else ''}: {resp!r}")
        if "detail" in resp and "id" not in resp and "_embedded" not in resp:
            raise RuntimeError(str(resp["detail"]))

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------
    def list_services(self) -> list[dict[str, Any]]:
        """Return all configured Policy Manager services."""
        logger.info("Fetching services from ClearPass")
        start = time.monotonic()
        resp = self._policy.get_config_service(limit=1000)
        self._check_error(resp, "list_services")
        items: list[dict[str, Any]] = resp.get("_embedded", {}).get("items", [])
        ms = (time.monotonic() - start) * 1000
        logger.info("Fetched %d service(s) from ClearPass (%.0f ms)", len(items), ms)
        return items

    def get_service(self, service_id: str) -> dict[str, Any] | None:
        """Return a single service by numeric ID, or None if not found."""
        logger.info("Fetching service id=%s from ClearPass", service_id)
        start = time.monotonic()
        resp = self._policy.get_config_service_by_services_id(services_id=service_id)
        ms = (time.monotonic() - start) * 1000
        if not isinstance(resp, dict) or "id" not in resp:
            detail = resp.get("detail", "") if isinstance(resp, dict) else str(resp)
            if "404" in str(detail) or "not found" in str(detail).lower():
                logger.info("Service id=%s not found (%.0f ms)", service_id, ms)
                return None
            if detail:
                logger.warning("ClearPass error fetching service id=%s: %s", service_id, detail)
                raise RuntimeError(str(detail))
            return None
        logger.info("Fetched service id=%s name=%r (%.0f ms)", service_id, resp.get("name"), ms)
        return resp

    # ------------------------------------------------------------------
    # Access Tracker / Insight
    # ------------------------------------------------------------------
    def list_access_tracker_records(
        self,
        *,
        filter_query: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return a page of Access Tracker session records via ApiLogs."""
        # TODO: confirm the correct ApiLogs method for Access Tracker records
        # and map the filter_query into the appropriate parameter format.
        logger.debug("list_access_tracker_records called (limit=%d, offset=%d)", limit, offset)
        raise NotImplementedError

    def get_access_tracker_record(self, record_id: str) -> dict[str, Any] | None:
        """Return a single Access Tracker record with full policy evaluation detail."""
        # TODO: confirm the correct ApiLogs method and whether a separate
        # session-details call is needed to get the full evaluation trail.
        logger.debug("get_access_tracker_record called (id=%s)", record_id)
        raise NotImplementedError


def get_clearpass_client(
    db: Annotated[Session, Depends(get_db)],
) -> ClearPassClient:
    """FastAPI dependency: builds a ClearPassClient from DB-stored config.

    Reads credentials from the app_settings row saved via the Settings UI.
    Falls back to environment variables if no DB config exists yet.
    Raises HTTP 503 if neither source has credentials configured.
    """
    row = db.get(AppSettings, 1)
    base_url = row.clearpass_base_url if row else None
    api_token = row.clearpass_api_token if row else None
    verify_ssl = row.clearpass_verify_ssl if row else True

    # Fall back to env vars when the DB config is not yet populated
    if not base_url or not api_token:
        try:
            from app.core.config import get_settings
            s = get_settings()
            base_url = base_url or s.clearpass_base_url
            api_token = api_token or s.clearpass_api_token
            verify_ssl = verify_ssl if row else s.clearpass_verify_ssl
        except Exception:
            pass

    if not base_url or not api_token:
        logger.warning("ClearPass client requested but server is not configured")
        raise HTTPException(
            status_code=503,
            detail=(
                "ClearPass server is not configured. "
                "Open Settings to enter the server URL and API token."
            ),
        )

    return ClearPassClient(base_url=base_url, api_token=api_token, verify_ssl=verify_ssl)
