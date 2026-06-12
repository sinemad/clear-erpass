from pydantic import BaseModel, HttpUrl


class ConfigRead(BaseModel):
    clearpass_base_url: str | None
    clearpass_api_token_configured: bool
    clearpass_verify_ssl: bool


class ConfigUpdate(BaseModel):
    clearpass_base_url: str
    clearpass_api_token: str | None = None  # None / empty = keep existing token
    clearpass_verify_ssl: bool = True
