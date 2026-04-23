from datetime import datetime

from pydantic import BaseModel, Field


class ShareCreateIn(BaseModel):
    expires_in_seconds: int = Field(ge=300, le=30 * 24 * 3600)
    allow_download: bool = False
    user_info: str = Field(min_length=1, max_length=64)


class ShareOut(BaseModel):
    token: str
    url: str
    content_id: int
    created_by: int
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    allow_download: bool
    state: str  # active | expired | revoked

    class Config:
        from_attributes = True


class ShareAccessOut(BaseModel):
    viewed_at: datetime
    client_ip_masked: str | None
    user_agent: str | None
    result: str


class ShareKeyOut(BaseModel):
    key: str
    user_id: int
    user_info: str
    is_used: bool
    used_at: datetime | None
    use_mode: str | None
    created_at: datetime


class OfflineOpenOut(BaseModel):
    token: str
    user_info: str | None
    opened_at: datetime | None
    reported_at: datetime
    is_offline_replay: bool
    user_agent: str | None
