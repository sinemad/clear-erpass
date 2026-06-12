"""Logging setup for the ClearPass Visualizer backend."""

from __future__ import annotations

import logging
import sys
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HTTP_LOGGER = logging.getLogger("app.http")

_LOG_BUFFER: deque[dict[str, Any]] = deque(maxlen=500)


class RingBufferHandler(logging.Handler):
    """Appends formatted log records to the in-memory ring buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            _LOG_BUFFER.append({
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            })
        except Exception:  # noqa: BLE001
            pass


def get_log_buffer() -> list[dict[str, Any]]:
    """Return a snapshot of the current ring buffer contents."""
    return list(_LOG_BUFFER)


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with a consistent format.

    Call once at application startup before any other code emits log records.
    Suppresses uvicorn.access (replaced by RequestLoggingMiddleware) and
    SQLAlchemy engine noise.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers = []
    root.addHandler(stream_handler)
    root.addHandler(RingBufferHandler())

    # Suppress loggers that would be noisy or duplicate our own output
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        ms = (time.monotonic() - start) * 1000
        _HTTP_LOGGER.info(
            "%s %s → %d (%.0f ms)",
            request.method,
            request.url.path,
            response.status_code,
            ms,
        )
        return response
