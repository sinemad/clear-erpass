"""Logs API route — serves the in-memory ring buffer to the web UI."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.logging_config import get_log_buffer

router = APIRouter(prefix="/api/logs", tags=["logs"])

LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class LogEntry(BaseModel):
    timestamp: str
    level: str
    logger: str
    message: str


@router.get("", response_model=list[LogEntry])
def get_logs(
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    level: Annotated[str | None, Query(description="Minimum level filter: DEBUG, INFO, WARNING, ERROR")] = None,
) -> list[LogEntry]:
    """Return recent log entries from the in-memory ring buffer.

    Results are ordered oldest-first. The buffer holds the last 500 entries;
    use `limit` to cap how many are returned.
    """
    level_order = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
    min_level = level_order.get(level.upper(), 0) if level else 0

    entries = [
        LogEntry(**e)
        for e in get_log_buffer()
        if level_order.get(e["level"], 0) >= min_level
    ]
    return entries[-limit:]
