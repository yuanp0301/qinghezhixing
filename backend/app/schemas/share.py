from datetime import datetime

from pydantic import BaseModel, Field


class ShareCreateIn(BaseModel):
    expires_in_seconds: int = Field(ge=300, le=30 * 24 * 3600)
    allow_download: bool = False


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
