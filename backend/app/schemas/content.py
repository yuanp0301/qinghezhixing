from pydantic import BaseModel, Field

from app.schemas.tag import TagOut


class ContentSummary(BaseModel):
    id: int
    title: str
    uploader_id: int
    uploader_username: str
    created_at: str
    size_bytes: int
    tags: list[TagOut]

    class Config:
        from_attributes = True


class ContentDetail(ContentSummary):
    description: str | None
    original_filename: str
    content_type: str
    sha256: str
    visibility: str
    status: str


class ContentUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = None
