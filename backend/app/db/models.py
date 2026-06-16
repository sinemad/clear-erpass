from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AppSettings(Base):
    """Single-row table storing the ClearPass connection config.

    Row id=1 is always the active config. Stored in SQLite so users can
    update it via the web UI without restarting the server.

    Note: credentials are stored in plaintext. This is acceptable for a
    single-user local tool; revisit if multi-user or network-exposed.
    """

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    clearpass_base_url: Mapped[str | None] = mapped_column(default=None)
    clearpass_client_id: Mapped[str | None] = mapped_column(default=None)
    clearpass_client_secret: Mapped[str | None] = mapped_column(default=None)
    # Internal cache — not user-configurable; populated by get_clearpass_client
    clearpass_api_token: Mapped[str | None] = mapped_column(default=None)
    clearpass_token_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    clearpass_verify_ssl: Mapped[bool] = mapped_column(default=True)
    debug_logging: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now()
    )
