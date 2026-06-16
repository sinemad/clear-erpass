from pydantic import BaseModel


class ConfigRead(BaseModel):
    clearpass_base_url: str | None
    clearpass_client_id: str | None
    clearpass_client_secret_configured: bool
    clearpass_verify_ssl: bool
    debug_logging: bool


class ConfigUpdate(BaseModel):
    clearpass_base_url: str
    clearpass_client_id: str
    clearpass_client_secret: str | None = None  # None / empty = keep existing
    clearpass_verify_ssl: bool = True
    debug_logging: bool = False
