def test_oss_settings(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "x" * 32)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@h:5432/d",
    )
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")
    monkeypatch.setenv("OSS_ENDPOINT", "https://oss.example.com")
    monkeypatch.setenv("OSS_BUCKET", "b")
    monkeypatch.setenv("OSS_ACCESS_KEY_ID", "id")
    monkeypatch.setenv("OSS_ACCESS_KEY_SECRET", "sk")
    monkeypatch.setenv("OSS_REGION", "cn-hangzhou")
    from app.config import Settings
    s = Settings()
    assert s.oss_bucket == "b"
    assert s.upload_max_bytes == 10 * 1024 * 1024
