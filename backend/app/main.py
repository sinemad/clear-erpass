import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import access_tracker, config, health, logs, services
from app.core.config import get_settings
from app.core.logging_config import RequestLoggingMiddleware, setup_logging

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(get_settings().log_level)
    logger.info("ClearPass Visualizer starting up")

    import app.db.models  # noqa: F401
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")

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
