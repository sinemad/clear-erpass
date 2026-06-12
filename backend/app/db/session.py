"""SQLAlchemy session factory.

v1 uses SQLite. Swap the engine URL via Settings.db_path when moving to
Postgres — the models should not need to change.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


def _engine():
    settings = get_settings()
    url = f"sqlite:///{settings.db_path}"
    return create_engine(url, connect_args={"check_same_thread": False})


engine = _engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
