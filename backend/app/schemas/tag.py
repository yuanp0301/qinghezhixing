import re

from pydantic import BaseModel, Field, field_validator

TAG_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9_\- ]{1,20}$")


class TagOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class TagAdminOut(TagOut):
    content_count: int
    created_at: str


class TagCreateIn(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _v(cls, v: str) -> str:
        v = v.strip()
        if not TAG_RE.match(v):
            raise ValueError("invalid tag name")
        return v


class TagRenameIn(BaseModel):
    name: str = Field(min_length=1, max_length=20)


class TagMergeIn(BaseModel):
    target_id: int
