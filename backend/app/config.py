from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_secret_key: str
    database_url: str

    session_cookie_name: str = "qh_session"
    session_ttl_seconds: int = 43200  # 12h
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


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
