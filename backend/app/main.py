import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine, text

from app.api import access_tracker, config, health, logs, services
from app.core.config import get_settings
from app.core.logging_config import RequestLoggingMiddleware, set_log_level, setup_logging

logger = logging.getLogger("app")


def _migrate_db(engine: Engine) -> None:
    """Add columns introduced after the initial schema without Alembic."""
    new_columns = [
        ("clearpass_client_id", "VARCHAR"),
        ("clearpass_client_secret", "VARCHAR"),
        ("clearpass_token_expires_at", "DATETIME"),
        ("debug_logging", "BOOLEAN NOT NULL DEFAULT 0"),
    ]
    with engine.connect() as conn:
        for col, col_type in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE app_settings ADD COLUMN {col} {col_type}"))
                conn.commit()
                logger.info("DB migration: added column app_settings.%s", col)
            except Exception:
                pass  # column already exists


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(get_settings().log_level)
    logger.info("ClearPass Visualizer starting up")

    import app.db.models  # noqa: F401
    from app.db.session import Base, SessionLocal, engine
    Base.metadata.create_all(bind=engine)
    _migrate_db(engine)
    logger.info("Database tables verified")

    from app.db.models import AppSettings
    with SessionLocal() as db:
        row = db.get(AppSettings, 1)
        if row and row.debug_logging:
            set_log_level("DEBUG")
            logger.info("Debug logging enabled (restored from settings)")

    yield

    logger.info("ClearPass Visualizer shutting down")


app = FastAPI(
    title="ClearPass Visualizer",
    description="Read-only visualization of Aruba ClearPass Policy Manager services and Access Tracker records.",
    version="0.1.0",
    lifespan=lifespan,
)

# RequestLoggingMiddleware must be added before CORSMiddleware so it sees
# the final response status code after CORS headers are applied.
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "PUT"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(config.router)
app.include_router(services.router)
app.include_router(access_tracker.router)
app.include_router(logs.router)
