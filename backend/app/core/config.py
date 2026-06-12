from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    clearpass_base_url: str
    clearpass_api_token: str
    clearpass_verify_ssl: bool = True

    db_path: str = "/data/clearpass_visualizer.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
