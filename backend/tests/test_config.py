import os
from app.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_SECRET_KEY", "x" * 32)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@h:5432/d",
    )
    s = Settings()
    assert s.app_env == "test"
    assert s.session_cookie_name == "qh_session"
    assert s.session_ttl_seconds == 43200


def test_settings_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "short")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@h:5432/d",
    )
    try:
        Settings()
    except Exception as e:
        assert "at least 32" in str(e)
    else:
        raise AssertionError("expected validation error")
