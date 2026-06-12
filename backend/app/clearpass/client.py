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

from typing import Annotated, Any

from fastapi import Depends, HTTPException
from pyclearpass import ClearPassAPILogin  # TODO: confirm import path/version
from sqlalchemy.orm import Session

from app.db.models import AppSettings
from app.db.session import get_db


class ClearPassClient:
    """Read-only wrapper around the ClearPass Policy Manager REST API.

    Only GET-equivalent operations should be added here. Do not add
    create/update/delete methods -- this project is read-only by design
    (see CLAUDE.md).
    """

    def __init__(self, base_url: str, api_token: str, verify_ssl: bool = True) -> None:
        self._login = ClearPassAPILogin(
            server=base_url,
            api_token=api_token,
            verify_ssl=verify_ssl,
        )
        # TODO: instantiate the relevant pyclearpass API category class(es),
        # e.g.:
        #   self._services_api = ApiPolicyServices(self._login)
        #   self._insight_api = ApiInsight(self._login)

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------
    def list_services(self) -> list[dict[str, Any]]:
        """Return the list of configured Policy Manager services (raw dicts).

        TODO: replace with the actual pyclearpass call, e.g.:
            return self._services_api.get_service(login=self._login)["_embedded"]["items"]
        """
        raise NotImplementedError

    def get_service(self, service_id: str) -> dict[str, Any]:
        """Return a single service definition by ID (raw dict).

        TODO: replace with the actual pyclearpass call.
        """
        raise NotImplementedError

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
        """Return a page of Access Tracker / Insight session records (raw dicts).

        `filter_query` follows ClearPass's REST filter syntax (e.g.
        `{"date_time": {"$gte": "2026-06-12T00:00:00Z"}}`).

        TODO: replace with the actual pyclearpass Insight/Access Tracker call,
        e.g.:
            return self._insight_api.get_insight_access_tracker(
                login=self._login, filter=filter_query, limit=limit, offset=offset
            )["_embedded"]["items"]
        """
        raise NotImplementedError

    def get_access_tracker_record(self, record_id: str) -> dict[str, Any]:
        """Return a single Access Tracker / Insight record with full detail
        (raw dict), including the policy evaluation trail needed to build the
        decision tree.

        TODO: replace with the actual pyclearpass call. Depending on the
        ClearPass version, the detailed evaluation trail may require a
        separate "session details" / "request details" endpoint in addition
        to the summary record -- if so, fetch and merge both here so callers
        get one complete dict.
        """
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
        raise HTTPException(
            status_code=503,
            detail=(
                "ClearPass server is not configured. "
                "Open Settings to enter the server URL and API token."
            ),
        )

    return ClearPassClient(base_url=base_url, api_token=api_token, verify_ssl=verify_ssl)
