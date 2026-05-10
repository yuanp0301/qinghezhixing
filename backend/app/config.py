from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_secret_key: str
    database_url: str

    session_cookie_name: str = "qh_session"
    session_ttl_seconds: int = 43200  # 12h
    cors_origins: str = Field(
        default="",
        description="Comma-separated browser origins; if set, enables CORS with credentials.",
    )
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    log_level: str = "INFO"

    oss_endpoint: str
    oss_internal_endpoint: str = ""
    oss_bucket: str
    oss_access_key_id: str
    oss_access_key_secret: str
    oss_region: str
    upload_max_bytes: int = 10 * 1024 * 1024

    share_min_seconds: int = 300
    share_max_seconds: int = 30 * 24 * 3600
    share_default_seconds: int = 24 * 3600
    public_base_url: str = "http://localhost:8000"

    @field_validator("app_secret_key")
    @classmethod
    def secret_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("APP_SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("session_cookie_samesite", mode="before")
    @classmethod
    def normalize_samesite(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v

    def session_cookie_use_secure(self) -> bool:
        if self.session_cookie_samesite == "none":
            return True
        return self.app_env != "dev"


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
