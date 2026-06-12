from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import access_tracker, config, health, services


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # Import models so SQLAlchemy registers them before create_all
    import app.db.models  # noqa: F401
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ClearPass Visualizer",
    description="Read-only visualization of Aruba ClearPass Policy Manager services and Access Tracker records.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET", "PUT"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(config.router)
app.include_router(services.router)
app.include_router(access_tracker.router)
