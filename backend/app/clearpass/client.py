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
from datetime import datetime, timedelta
from typing import Annotated, Any

import json

import requests as _requests
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
        api_url = _api_base(base_url)
        logger.debug("Initializing ClearPass client for %s (verify_ssl=%s)", api_url, verify_ssl)
        self._api_url = api_url
        self._api_token = api_token
        self._verify_ssl = verify_ssl
        kwargs = dict(server=api_url, api_token=api_token, verify_ssl=verify_ssl)
        self._policy = ApiPolicyElements(**kwargs)
        self._logs = ApiLogs(**kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make an authenticated GET request to the ClearPass REST API."""
        url = f"{self._api_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Accept": "application/json",
        }
        resp = _requests.get(
            url, params=params, headers=headers,
            verify=self._verify_ssl, timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _check_error(resp: Any, context: str = "") -> None:
        """Raise RuntimeError if pyclearpass returned an API-level error dict."""
        if not isinstance(resp, dict):
            raise RuntimeError(f"Unexpected ClearPass response{f' ({context})' if context else ''}: {resp!r}")
        if "detail" in resp and "id" not in resp and "_embedded" not in resp:
            raise RuntimeError(str(resp["detail"]))

    def _fetch_by_name(self, method_name: str, name: str) -> dict[str, Any] | None:
        """Call a pyclearpass ApiPolicyElements 'get_X_name_by_name' method safely.

        Returns the response dict if it looks valid (has an 'id' key), None on
        404 or any other error. Errors are logged at DEBUG level and suppressed
        so a missing policy never blocks the whole tree from rendering.
        """
        if not name:
            return None
        try:
            resp = getattr(self._policy, method_name)(name=name)
            if isinstance(resp, dict) and "id" in resp:
                return resp
            logger.debug("%s(name=%r) returned no valid data", method_name, name)
            return None
        except Exception as exc:
            logger.debug("%s(name=%r) failed: %s", method_name, name, exc)
            return None

    # ------------------------------------------------------------------
    # Policy element lookups (by name)
    # ------------------------------------------------------------------

    def get_role_mapping(self, name: str) -> dict[str, Any] | None:
        logger.debug("Fetching role mapping policy: %r", name)
        return self._fetch_by_name("get_role_mapping_name_by_name", name)

    def get_enforcement_policy(self, name: str) -> dict[str, Any] | None:
        logger.debug("Fetching enforcement policy: %r", name)
        return self._fetch_by_name("get_enforcement_policy_name_by_name", name)

    def get_auth_method(self, name: str) -> dict[str, Any] | None:
        logger.debug("Fetching auth method: %r", name)
        return self._fetch_by_name("get_auth_method_name_by_name", name)

    def get_auth_source(self, name: str) -> dict[str, Any] | None:
        logger.debug("Fetching auth source: %r", name)
        return self._fetch_by_name("get_auth_source_name_by_name", name)

    def get_posture_policy(self, name: str) -> dict[str, Any] | None:
        logger.debug("Fetching posture policy: %r", name)
        return self._fetch_by_name("get_posture_policy_name_by_name", name)

    def get_enforcement_profile(self, name: str) -> dict[str, Any] | None:
        logger.debug("Fetching enforcement profile: %r", name)
        return self._fetch_by_name("get_enforcement_profile_name_by_name", name)

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------
    def list_services(self) -> list[dict[str, Any]]:
        """Return all configured Policy Manager services."""
        logger.info("Fetching services from ClearPass")
        start = time.monotonic()
        resp = self._policy.get_config_service(limit=1000)
        logger.warning("list_services raw response: %r", resp)
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
        """Return a page of Access Tracker authentication records.

        Uses the ClearPass /accounting/auth REST endpoint with an optional
        JSON filter.  The filter_query dict is serialised as the ``filter``
        query-string parameter, e.g. ``{"service_name": "Wireless 802.1X"}``.
        """
        logger.debug(
            "list_access_tracker_records called (filter=%r, limit=%d, offset=%d)",
            filter_query, limit, offset,
        )
        params: dict[str, Any] = {
            "sort": "-timestamp",
            "limit": limit,
            "offset": offset,
        }
        if filter_query:
            params["filter"] = json.dumps(filter_query)

        try:
            resp = self._get("/accounting/auth", params=params)
        except _requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                # ClearPass returns 404 (not 200 + empty list) when a filtered
                # query matches no records.  Log the full body at WARNING so
                # that a misconfigured endpoint or permissions issue is still
                # visible in the logs, but return [] so the UI shows
                # "no records" rather than an error.
                logger.warning(
                    "Access Tracker returned 404 — no records found (filter=%r)",
                    filter_query,
                )
                return []
            raise
        items: list[dict[str, Any]] = resp.get("_embedded", {}).get("items", [])
        logger.info("list_access_tracker_records returned %d record(s)", len(items))
        return items

    def get_access_tracker_record(self, record_id: str) -> dict[str, Any] | None:
        """Return a single Access Tracker record by ID, or None if not found."""
        logger.debug("get_access_tracker_record called (id=%s)", record_id)
        try:
            resp = self._get(f"/accounting/auth/{record_id}")
        except _requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                logger.info("Access Tracker record id=%s not found", record_id)
                return None
            raise
        if not isinstance(resp, dict) or "id" not in resp:
            logger.warning("Unexpected response for record id=%s: %r", record_id, resp)
            return None
        return resp


def _api_base(base_url: str) -> str:
    url = base_url.rstrip("/")
    return url if url.endswith("/api") else f"{url}/api"


def _fetch_oauth_token(
    base_url: str, client_id: str, client_secret: str, verify_ssl: bool
) -> tuple[str, datetime]:
    """Exchange client credentials for an OAuth2 access token."""
    url = f"{_api_base(base_url)}/oauth"
    logger.info("Fetching OAuth2 token from %s (client_id=%s)", url, client_id)
    resp = _requests.post(
        url,
        json={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
        verify=verify_ssl,
        timeout=15,
    )
    if not resp.ok:
        logger.error("OAuth2 token request failed: %s %r", resp.status_code, resp.text)
        raise RuntimeError(f"ClearPass OAuth2 error {resp.status_code}: {resp.text}")
    data = resp.json()
    access_token: str = data["access_token"]
    expires_in: int = data.get("expires_in", 28800)
    # Subtract 60 s so we refresh before the token actually expires
    expires_at = datetime.utcnow() + timedelta(seconds=max(expires_in - 60, 0))
    logger.info("OAuth2 token obtained (expires_in=%ds)", expires_in)
    return access_token, expires_at


def get_clearpass_client(
    db: Annotated[Session, Depends(get_db)],
) -> ClearPassClient:
    """FastAPI dependency: builds a ClearPassClient using OAuth2 client credentials.

    Caches the access token in the DB and refreshes it automatically when it
    nears expiry. Raises HTTP 503 if the server or credentials are not configured.
    """
    row = db.get(AppSettings, 1)
    base_url = row.clearpass_base_url if row else None
    client_id = row.clearpass_client_id if row else None
    client_secret = row.clearpass_client_secret if row else None
    verify_ssl = row.clearpass_verify_ssl if row else True

    if not base_url or not client_id or not client_secret:
        logger.warning("ClearPass client requested but credentials are not configured")
        raise HTTPException(
            status_code=503,
            detail=(
                "ClearPass server is not configured. "
                "Open Settings to enter the server URL, Client ID, and Client Secret."
            ),
        )

    # Refresh the cached token if missing or within 60 s of expiry
    now = datetime.utcnow()
    if (
        not row.clearpass_api_token
        or not row.clearpass_token_expires_at
        or row.clearpass_token_expires_at <= now
    ):
        try:
            token, expires_at = _fetch_oauth_token(base_url, client_id, client_secret, verify_ssl)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"ClearPass OAuth2 error: {exc}") from exc
        row.clearpass_api_token = token
        row.clearpass_token_expires_at = expires_at
        db.commit()

    return ClearPassClient(base_url=base_url, api_token=row.clearpass_api_token, verify_ssl=verify_ssl)
