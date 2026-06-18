from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


def _str_list(val: Any) -> list[str]:
    """Coerce a ClearPass value (string, list, or None) into a list of strings."""
    if not val:
        return []
    if isinstance(val, str):
        return [val] if val.strip() else []
    if isinstance(val, list):
        return [str(v) for v in val if v]
    return [str(val)]


class AccessTrackerSummary(BaseModel):
    """Summary row for the Access Tracker drawer / table view."""

    id: str
    timestamp: datetime
    service_name: str
    username: str | None = None
    endpoint_mac: str | None = None
    ip_address: str | None = None
    auth_status: str = ""  # ACCEPT | REJECT | TIMEOUT | ERROR | DROP

    @model_validator(mode="before")
    @classmethod
    def _map_clearpass_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        # MAC address — ClearPass uses mac_address
        if "endpoint_mac" not in d or d["endpoint_mac"] is None:
            d["endpoint_mac"] = d.get("mac_address")
        # Auth status — normalise to uppercase
        raw_status = d.get("auth_status") or d.get("status") or ""
        d["auth_status"] = str(raw_status).upper()
        return d


class AccessTrackerDetail(BaseModel):
    """Full Access Tracker record returned by the detail endpoint."""

    id: str
    timestamp: datetime
    service_name: str
    username: str | None = None
    endpoint_mac: str | None = None
    ip_address: str | None = None
    auth_status: str = ""
    auth_method: str | None = None
    auth_source: str | None = None
    roles: list[str] = Field(default_factory=list)
    enforcement_profiles: list[str] = Field(default_factory=list)
    error_code: int | None = None
    error_message: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _map_clearpass_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if "endpoint_mac" not in d or d["endpoint_mac"] is None:
            d["endpoint_mac"] = d.get("mac_address")
        raw_status = d.get("auth_status") or d.get("status") or ""
        d["auth_status"] = str(raw_status).upper()
        # Roles and enforcement profiles may be lists or comma-separated strings
        d["roles"] = _str_list(d.get("roles") or d.get("role"))
        d["enforcement_profiles"] = _str_list(
            d.get("enforcement_profiles") or d.get("enforcement_profile")
        )
        # Error fields
        if "error_message" not in d or d["error_message"] is None:
            d["error_message"] = d.get("error_string") or d.get("error_msg")
        return d
