# Plan 2 / 5 — Content & OSS 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Plan 1 的基础上，实现「互动动画」内容主体能力——OSS 客户端封装、`contents`/`tags`/`content_tags`/`view_logs` 数据模型、上传校验与入库、列表/详情/编辑/软删 API、内嵌观看的 `/view/{id}` 代理（CSP + sandbox），以及标签管理 API。

**Architecture:** 文件存阿里云 OSS（私有读），Object key `contents/{yyyy}/{mm}/{uuid}.html`。上传走 `multipart/form-data`，先做白名单 + 大小 + 真实类型 + sha256 校验，再 PutObject，最后写库；事务失败时反向删 OSS 对象。`/view/{id}` 后端代理 GetObject 流式回写，附 CSP `sandbox; default-src 'self' data:` 等头。无签名 URL 直接外发。

**Tech Stack:** 沿用 Plan 1。新增：`oss2`（阿里云 OSS SDK，签名 V4）、`python-magic` 或最简首字节嗅探。本计划用首字节嗅探避免引入二进制依赖。

**前置:** Plan 1 全部完成；docker-compose 起，alembic 已 head。

**Spec 引用:**
- 设计文档 §3.1/3.2、§4（contents/tags/content_tags/view_logs）、§5.2（站内内容接口）、§5.6（标签）、§6.1/6.3/6.4。
- PRD §2 公开库、§3 详情/观看、§4 上传页、§6 我的上传（API 部分）、§8.3 标签管理（API 部分）。

---

## 文件结构（在 Plan 1 之上新增）

```
app/
  oss/
    __init__.py
    client.py            # oss2 client 工厂
    storage.py           # put_object / get_object_stream / delete_object
  models/
    content.py           # Content
    tag.py               # Tag, ContentTag
    view_log.py          # ViewLog
  schemas/
    content.py
    tag.py
  services/
    contents.py
    tags.py
    upload_validation.py # 类型/大小/sha256
  api/
    contents.py          # /api/contents/*
    view.py              # GET /view/{id}
    tags.py              # /api/tags
    admin_tags.py        # /api/admin/tags/*
alembic/versions/
  0002_contents_tags_views.py
tests/
  test_oss_storage.py        # 用 stub
  test_upload_validation.py
  test_contents_api.py
  test_view_proxy.py
  test_tags_api.py
```

---

### Task 1: 依赖与配置扩展

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `app/config.py`
- Create: `tests/test_config_oss.py`

- [ ] **Step 1: 加依赖到 `pyproject.toml`**

在 `dependencies` 中追加：

```toml
"oss2>=2.18",
"aiofiles>=23.2",
```

Run: `pip install -e ".[dev]"` 安装。

- [ ] **Step 2: 追加 `.env.example`**

```
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
OSS_INTERNAL_ENDPOINT=
OSS_BUCKET=qinghe-dev
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_REGION=cn-hangzhou
UPLOAD_MAX_BYTES=10485760
```

- [ ] **Step 3: 扩展 `app/config.py` Settings**

在 `Settings` 中追加字段：

```python
    oss_endpoint: str
    oss_internal_endpoint: str = ""
    oss_bucket: str
    oss_access_key_id: str
    oss_access_key_secret: str
    oss_region: str
    upload_max_bytes: int = 10 * 1024 * 1024
```

- [ ] **Step 4: 写测试 `tests/test_config_oss.py`**

```python
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
```

- [ ] **Step 5: 运行 + 提交**

Run: `pytest tests/test_config_oss.py -v`
Expected: 1 passed。

```bash
git add pyproject.toml .env.example app/config.py tests/test_config_oss.py
git commit -m "chore(config): add OSS settings and upload size limit"
```

---

### Task 2: OSS 客户端封装

**Files:**
- Create: `app/oss/__init__.py`（空）
- Create: `app/oss/client.py`
- Create: `app/oss/storage.py`

- [ ] **Step 1: `app/oss/client.py`**

```python
import oss2

from app.config import get_settings

_settings = get_settings()


def make_bucket() -> oss2.Bucket:
    auth = oss2.AuthV4(
        _settings.oss_access_key_id,
        _settings.oss_access_key_secret,
    )
    endpoint = (
        _settings.oss_internal_endpoint or _settings.oss_endpoint
    )
    return oss2.Bucket(
        auth,
        endpoint,
        _settings.oss_bucket,
        region=_settings.oss_region,
    )
```

- [ ] **Step 2: `app/oss/storage.py`**

```python
from collections.abc import Iterator
from typing import BinaryIO

from app.oss.client import make_bucket


def put_object(
    object_key: str, data: BinaryIO, content_type: str
) -> dict:
    bucket = make_bucket()
    headers = {"Content-Type": content_type}
    resp = bucket.put_object(object_key, data, headers=headers)
    return {
        "etag": resp.etag,
        "request_id": resp.request_id,
    }


def stream_object(object_key: str) -> Iterator[bytes]:
    bucket = make_bucket()
    obj = bucket.get_object(object_key)
    try:
        while True:
            chunk = obj.read(64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        obj.close()


def delete_object(object_key: str) -> None:
    bucket = make_bucket()
    bucket.delete_object(object_key)
```

> 说明：oss2 是同步 SDK；FastAPI 的 endpoint 中用 `await asyncio.to_thread(...)` 调用即可。本模块保持同步风格。

- [ ] **Step 3: 提交**

```bash
git add app/oss/
git commit -m "feat(oss): bucket factory and basic put/get/delete wrappers"
```

---

### Task 3: 上传校验工具（类型/大小/sha256）

**Files:**
- Create: `app/services/upload_validation.py`
- Create: `tests/test_upload_validation.py`

- [ ] **Step 1: 测试**

```python
from io import BytesIO

import pytest

from app.services.upload_validation import (
    UploadValidationError,
    validate_html_upload,
)


def _bytes_io(b: bytes) -> BytesIO:
    s = BytesIO(b)
    return s


def test_accept_minimal_html():
    body = b"<!DOCTYPE html><html><body>ok</body></html>"
    info = validate_html_upload(
        filename="a.html",
        content_type="text/html",
        stream=_bytes_io(body),
        max_bytes=10_000,
    )
    assert info.size == len(body)
    assert info.sha256 and len(info.sha256) == 64


def test_reject_wrong_extension():
    with pytest.raises(UploadValidationError, match="extension"):
        validate_html_upload(
            filename="a.pdf",
            content_type="text/html",
            stream=_bytes_io(b"<html></html>"),
            max_bytes=1000,
        )


def test_reject_wrong_mime():
    with pytest.raises(UploadValidationError, match="mime"):
        validate_html_upload(
            filename="a.html",
            content_type="application/octet-stream",
            stream=_bytes_io(b"<html></html>"),
            max_bytes=1000,
        )


def test_reject_too_large():
    with pytest.raises(UploadValidationError, match="size"):
        validate_html_upload(
            filename="a.html",
            content_type="text/html",
            stream=_bytes_io(b"x" * 2000),
            max_bytes=1000,
        )


def test_reject_non_html_first_bytes():
    with pytest.raises(UploadValidationError, match="content"):
        validate_html_upload(
            filename="a.html",
            content_type="text/html",
            stream=_bytes_io(b"%PDF-1.4 fake fake"),
            max_bytes=1000,
        )
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_upload_validation.py -v`
Expected: ImportError。

- [ ] **Step 3: 实现 `app/services/upload_validation.py`**

```python
import hashlib
import re
from dataclasses import dataclass
from typing import BinaryIO

_HTML_SNIFF_RE = re.compile(
    rb"^\s*(<!doctype\s+html|<html|<head|<body|<meta|<script|<svg)",
    re.IGNORECASE,
)


class UploadValidationError(ValueError):
    pass


@dataclass
class UploadInfo:
    size: int
    sha256: str


def validate_html_upload(
    *,
    filename: str,
    content_type: str,
    stream: BinaryIO,
    max_bytes: int,
) -> UploadInfo:
    if not filename.lower().endswith(".html"):
        raise UploadValidationError(
            "invalid extension: only .html is allowed"
        )
    if content_type not in {"text/html", "text/html; charset=utf-8"}:
        raise UploadValidationError(
            f"invalid mime: got {content_type!r}, expect text/html"
        )

    stream.seek(0)
    head = stream.read(512)
    if not _HTML_SNIFF_RE.search(head):
        raise UploadValidationError(
            "invalid content: file does not look like HTML"
        )

    h = hashlib.sha256()
    h.update(head)
    size = len(head)
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise UploadValidationError(
                f"size exceeded: > {max_bytes} bytes"
            )
        h.update(chunk)

    stream.seek(0)
    return UploadInfo(size=size, sha256=h.hexdigest())
```

- [ ] **Step 4: 测试通过 + 提交**

Run: `pytest tests/test_upload_validation.py -v`
Expected: 5 passed。

```bash
git add app/services/upload_validation.py tests/test_upload_validation.py
git commit -m "feat(upload): validate html uploads (ext/mime/size/sniff/sha256)"
```

---

### Task 4: 内容相关模型

**Files:**
- Create: `app/models/content.py`
- Create: `app/models/tag.py`
- Create: `app/models/view_log.py`
- Modify: `alembic/env.py` 加新模型导入
- Create: `alembic/versions/0002_contents_tags_views.py`（autogen 后改名）

- [ ] **Step 1: `app/models/content.py`**

```python
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uploader_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    oss_bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    oss_object_key: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'public_in_site'"),
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'active'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="content_tags",
        back_populates="contents",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public_in_site','private')",
            name="ck_contents_visibility",
        ),
        CheckConstraint(
            "status IN ('active','deleted')", name="ck_contents_status"
        ),
        Index("ix_contents_uploader_created", "uploader_id", "created_at"),
        Index("ix_contents_visibility_created", "visibility", "created_at"),
        Index("ix_contents_sha256", "sha256"),
    )
```

- [ ] **Step 2: `app/models/tag.py`**

```python
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    contents: Mapped[list["Content"]] = relationship(  # noqa: F821
        secondary="content_tags",
        back_populates="tags",
    )


class ContentTag(Base):
    __tablename__ = "content_tags"

    content_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("contents.id", ondelete="CASCADE"),
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tags.id", ondelete="CASCADE"),
    )

    __table_args__ = (
        PrimaryKeyConstraint("content_id", "tag_id"),
        Index("ix_content_tags_tag", "tag_id"),
    )
```

- [ ] **Step 3: `app/models/view_log.py`**

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ViewLog(Base):
    __tablename__ = "view_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    content_id: Mapped[int | None] = mapped_column(BigInteger)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    client_ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(255))
```

- [ ] **Step 4: 在 `alembic/env.py` 顶部追加导入**

```python
from app.models import content as _content  # noqa: F401
from app.models import tag as _tag  # noqa: F401
from app.models import view_log as _view  # noqa: F401
```

- [ ] **Step 5: 生成并应用迁移**

Run: `alembic revision --autogenerate -m "contents tags views"`
重命名为 `0002_contents_tags_views.py`。

Run: `alembic upgrade head`
Expected: 4 张新表（contents、tags、content_tags、view_logs）出现。

- [ ] **Step 6: 提交**

```bash
git add app/models/ alembic/env.py alembic/versions/0002_*.py
git commit -m "feat(db): add contents, tags, content_tags, view_logs"
```

---

### Task 5: 标签 service

**Files:**
- Create: `app/services/tags.py`
- Create: `app/schemas/tag.py`
- Create: `tests/test_tags_service.py`

- [ ] **Step 1: `app/schemas/tag.py`**

```python
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
```

- [ ] **Step 2: `app/services/tags.py`**

```python
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import ContentTag, Tag


async def get_or_create_many(
    db: AsyncSession, names: list[str]
) -> list[Tag]:
    names = [n.strip() for n in names if n.strip()]
    if not names:
        return []
    existing = (
        await db.execute(select(Tag).where(Tag.name.in_(names)))
    ).scalars().all()
    by_name = {t.name: t for t in existing}
    result: list[Tag] = []
    for n in names:
        if n in by_name:
            result.append(by_name[n])
        else:
            t = Tag(name=n)
            db.add(t)
            await db.flush()
            by_name[n] = t
            result.append(t)
    return result


async def list_all(db: AsyncSession, q: str | None = None) -> list[Tag]:
    stmt = select(Tag).order_by(Tag.name)
    if q:
        stmt = stmt.where(Tag.name.ilike(f"%{q}%"))
    return list((await db.execute(stmt)).scalars().all())


async def list_admin(db: AsyncSession, q: str | None = None):
    stmt = (
        select(
            Tag,
            func.count(ContentTag.content_id).label("cnt"),
        )
        .outerjoin(ContentTag, ContentTag.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(Tag.name)
    )
    if q:
        stmt = stmt.where(Tag.name.ilike(f"%{q}%"))
    rows = (await db.execute(stmt)).all()
    return [(t, cnt) for t, cnt in rows]


async def rename(db: AsyncSession, tag_id: int, new_name: str) -> Tag:
    t = await db.get(Tag, tag_id)
    if not t:
        raise LookupError("tag not found")
    dup = (
        await db.execute(select(Tag).where(Tag.name == new_name))
    ).scalar_one_or_none()
    if dup and dup.id != tag_id:
        raise ValueError("name taken")
    t.name = new_name
    await db.flush()
    return t


async def delete_unused(db: AsyncSession, tag_id: int) -> None:
    cnt = (
        await db.execute(
            select(func.count(ContentTag.content_id)).where(
                ContentTag.tag_id == tag_id
            )
        )
    ).scalar_one()
    if cnt > 0:
        raise ValueError("tag in use")
    await db.execute(delete(Tag).where(Tag.id == tag_id))


async def merge(
    db: AsyncSession, source_id: int, target_id: int
) -> int:
    if source_id == target_id:
        raise ValueError("same tag")
    src = await db.get(Tag, source_id)
    tgt = await db.get(Tag, target_id)
    if not src or not tgt:
        raise LookupError("tag not found")

    # 重指。先删除已与 target 同存的 source 关联，避免 PK 冲突。
    await db.execute(
        delete(ContentTag).where(
            ContentTag.tag_id == source_id,
            ContentTag.content_id.in_(
                select(ContentTag.content_id).where(
                    ContentTag.tag_id == target_id
                )
            ),
        )
    )
    affected = (
        await db.execute(
            ContentTag.__table__.update()
            .where(ContentTag.tag_id == source_id)
            .values(tag_id=target_id)
        )
    ).rowcount
    await db.execute(delete(Tag).where(Tag.id == source_id))
    return affected or 0
```

- [ ] **Step 3: 测试 `tests/test_tags_service.py`**

```python
import pytest

from app.services import tags as svc


@pytest.mark.asyncio
async def test_get_or_create_dedupes(db):
    a = await svc.get_or_create_many(db, ["x", "y", "x"])
    assert {t.name for t in a} == {"x", "y"}
    b = await svc.get_or_create_many(db, ["x", "z"])
    names = {t.name for t in b}
    assert names == {"x", "z"}


@pytest.mark.asyncio
async def test_rename_and_delete(db):
    [t] = await svc.get_or_create_many(db, ["foo"])
    r = await svc.rename(db, t.id, "foo2")
    assert r.name == "foo2"
    await svc.delete_unused(db, t.id)
```

- [ ] **Step 4: 运行 + 提交**

Run: `pytest tests/test_tags_service.py -v`
Expected: 2 passed。

```bash
git add app/schemas/tag.py app/services/tags.py tests/test_tags_service.py
git commit -m "feat(tags): get-or-create, list, rename, delete, merge"
```

---

### Task 6: contents service（创建/查询/编辑/软删）

**Files:**
- Create: `app/schemas/content.py`
- Create: `app/services/contents.py`
- Create: `tests/test_contents_service.py`

- [ ] **Step 1: `app/schemas/content.py`**

```python
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
```

- [ ] **Step 2: `app/services/contents.py`**

```python
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Content
from app.models.tag import ContentTag, Tag
from app.models.user import User
from app.services import tags as tag_svc


async def create_content(
    db: AsyncSession,
    *,
    uploader_id: int,
    title: str,
    description: str | None,
    oss_bucket: str,
    oss_object_key: str,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
    tag_names: list[str],
) -> Content:
    c = Content(
        uploader_id=uploader_id,
        title=title,
        description=description,
        oss_bucket=oss_bucket,
        oss_object_key=oss_object_key,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=sha256,
    )
    db.add(c)
    await db.flush()
    if tag_names:
        tags = await tag_svc.get_or_create_many(db, tag_names)
        for t in tags:
            db.add(ContentTag(content_id=c.id, tag_id=t.id))
        await db.flush()
    return c


async def get_active(
    db: AsyncSession, content_id: int
) -> Content | None:
    stmt = (
        select(Content)
        .where(Content.id == content_id, Content.status == "active")
        .options(selectinload(Content.tags))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_public(
    db: AsyncSession,
    *,
    q: str | None,
    tag: str | None,
    order: str,
    page: int,
    size: int,
) -> tuple[Sequence[Content], int]:
    base = (
        select(Content)
        .where(
            Content.visibility == "public_in_site",
            Content.status == "active",
        )
        .options(selectinload(Content.tags))
    )
    cnt = select(func.count(Content.id)).where(
        Content.visibility == "public_in_site",
        Content.status == "active",
    )
    if q:
        like = f"%{q}%"
        base = base.where(Content.title.ilike(like))
        cnt = cnt.where(Content.title.ilike(like))
    if tag:
        sub = select(ContentTag.content_id).join(
            Tag, Tag.id == ContentTag.tag_id
        ).where(Tag.name == tag)
        base = base.where(Content.id.in_(sub))
        cnt = cnt.where(Content.id.in_(sub))
    base = base.order_by(
        Content.created_at.asc()
        if order == "oldest"
        else Content.created_at.desc()
    ).offset((page - 1) * size).limit(size)

    rows = (await db.execute(base)).scalars().all()
    total = (await db.execute(cnt)).scalar_one()
    return rows, total


async def list_mine(
    db: AsyncSession,
    *,
    user_id: int,
    q: str | None,
    tag: str | None,
    page: int,
    size: int,
) -> tuple[Sequence[Content], int]:
    base = (
        select(Content)
        .where(Content.uploader_id == user_id, Content.status == "active")
        .options(selectinload(Content.tags))
    )
    cnt = select(func.count(Content.id)).where(
        Content.uploader_id == user_id, Content.status == "active"
    )
    if q:
        base = base.where(Content.title.ilike(f"%{q}%"))
        cnt = cnt.where(Content.title.ilike(f"%{q}%"))
    if tag:
        sub = select(ContentTag.content_id).join(
            Tag, Tag.id == ContentTag.tag_id
        ).where(Tag.name == tag)
        base = base.where(Content.id.in_(sub))
        cnt = cnt.where(Content.id.in_(sub))
    base = base.order_by(Content.created_at.desc()).offset(
        (page - 1) * size
    ).limit(size)
    rows = (await db.execute(base)).scalars().all()
    total = (await db.execute(cnt)).scalar_one()
    return rows, total


async def update_content(
    db: AsyncSession,
    *,
    content: Content,
    title: str | None,
    description: str | None,
    tags: list[str] | None,
) -> Content:
    if title is not None:
        content.title = title
    if description is not None:
        content.description = description
    if tags is not None:
        # 替换标签集
        await db.execute(
            ContentTag.__table__.delete().where(
                ContentTag.content_id == content.id
            )
        )
        new_tags = await tag_svc.get_or_create_many(db, tags)
        for t in new_tags:
            db.add(ContentTag(content_id=content.id, tag_id=t.id))
    await db.flush()
    return content


async def soft_delete(db: AsyncSession, content: Content) -> None:
    content.status = "deleted"
    await db.flush()


async def to_summary_dict(
    db: AsyncSession, c: Content
) -> dict[str, Any]:
    uploader_username = (
        await db.execute(
            select(User.username).where(User.id == c.uploader_id)
        )
    ).scalar_one()
    return {
        "id": c.id,
        "title": c.title,
        "uploader_id": c.uploader_id,
        "uploader_username": uploader_username,
        "created_at": c.created_at.isoformat(),
        "size_bytes": c.size_bytes,
        "tags": [{"id": t.id, "name": t.name} for t in c.tags],
    }
```

- [ ] **Step 3: 测试 `tests/test_contents_service.py`**

```python
import pytest

from app.schemas.user import UserCreateIn
from app.services import contents as cs
from app.services import users as us


@pytest.mark.asyncio
async def test_create_and_query(db):
    u = await us.create_user(
        db,
        UserCreateIn(
            username="creator9",
            password="Passw0rd!",
            role="creator",
        ),
    )
    c = await cs.create_content(
        db,
        uploader_id=u.id,
        title="Hello",
        description=None,
        oss_bucket="b",
        oss_object_key="contents/2026/04/abc.html",
        original_filename="hello.html",
        content_type="text/html",
        size_bytes=10,
        sha256="0" * 64,
        tag_names=["演示", "Demo"],
    )
    assert c.id

    rows, total = await cs.list_public(
        db, q=None, tag="演示", order="newest", page=1, size=10
    )
    assert total == 1
    assert rows[0].id == c.id


@pytest.mark.asyncio
async def test_update_and_soft_delete(db):
    u = await us.create_user(
        db,
        UserCreateIn(
            username="creatorA",
            password="Passw0rd!",
            role="creator",
        ),
    )
    c = await cs.create_content(
        db,
        uploader_id=u.id,
        title="t",
        description=None,
        oss_bucket="b",
        oss_object_key="contents/x.html",
        original_filename="x.html",
        content_type="text/html",
        size_bytes=1,
        sha256="0" * 64,
        tag_names=[],
    )
    await cs.update_content(
        db, content=c, title="t2", description="d", tags=["A"]
    )
    assert c.title == "t2"
    assert {t.name for t in c.tags} == {"A"}

    await cs.soft_delete(db, c)
    assert await cs.get_active(db, c.id) is None
```

- [ ] **Step 4: 运行 + 提交**

Run: `pytest tests/test_contents_service.py -v`
Expected: 2 passed。

```bash
git add app/schemas/content.py app/services/contents.py tests/test_contents_service.py
git commit -m "feat(contents): create/list/update/soft-delete service"
```

---

### Task 7: OSS storage 单测（用 stub）

**Files:**
- Create: `tests/test_oss_storage.py`

> 不接真实 OSS。用 monkeypatch 覆盖 `make_bucket`，验证调用形态。

- [ ] **Step 1: 测试**

```python
from io import BytesIO
from typing import Any

import pytest

from app.oss import storage


class FakeResp:
    etag = "FAKEETAG"
    request_id = "REQ-1"


class FakeStreamObj:
    def __init__(self):
        self._data = [b"hello ", b"world"]
        self._i = 0

    def read(self, n: int) -> bytes:
        if self._i >= len(self._data):
            return b""
        c = self._data[self._i]
        self._i += 1
        return c

    def close(self) -> None:
        pass


class FakeBucket:
    def __init__(self):
        self.calls: list[Any] = []

    def put_object(self, key, data, headers):
        self.calls.append(("put", key, headers))
        return FakeResp()

    def get_object(self, key):
        self.calls.append(("get", key))
        return FakeStreamObj()

    def delete_object(self, key):
        self.calls.append(("del", key))


def test_put_get_delete(monkeypatch):
    fake = FakeBucket()
    monkeypatch.setattr(storage, "make_bucket", lambda: fake)

    info = storage.put_object(
        "k", BytesIO(b"abc"), "text/html"
    )
    assert info["etag"] == "FAKEETAG"

    chunks = list(storage.stream_object("k"))
    assert b"".join(chunks) == b"hello world"

    storage.delete_object("k")
    kinds = [c[0] for c in fake.calls]
    assert kinds == ["put", "get", "del"]
```

- [ ] **Step 2: 运行 + 提交**

Run: `pytest tests/test_oss_storage.py -v`
Expected: 1 passed。

```bash
git add tests/test_oss_storage.py
git commit -m "test(oss): cover put/get/delete with stub bucket"
```

---

### Task 8: 上传 API（POST /api/contents）

**Files:**
- Create: `app/api/contents.py`
- Modify: `app/main.py`
- Create: `tests/test_contents_upload_api.py`

> 设计要点：
> - 用 `UploadFile` 接收文件，先校验 → 算 OSS key（`contents/{yyyy}/{mm}/{uuid}.html`）→ `to_thread(put_object, ...)` → 写库 → audit → commit。
> - 任何写库失败：调用 `delete_object` 反向回滚 OSS。
> - 标签作为 `tags` 多值表单字段（`tags=a&tags=b`）。

- [ ] **Step 1: `app/api/contents.py`（先只放 POST）**

```python
import asyncio
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.oss import storage
from app.schemas.content import ContentDetail
from app.services import contents as cs
from app.services.audit import write_audit
from app.services.upload_validation import (
    UploadValidationError,
    validate_html_upload,
)

settings = get_settings()
router = APIRouter(prefix="/api/contents", tags=["contents"])


def _build_object_key(now: datetime) -> str:
    return f"contents/{now:%Y}/{now:%m}/{uuid.uuid4().hex}.html"


@router.post(
    "",
    response_model=ContentDetail,
    status_code=201,
    dependencies=[Depends(require_role("creator", "admin"))],
)
async def upload_content(
    title: str = Form(min_length=1, max_length=100),
    description: str | None = Form(default=None, max_length=500),
    tags: list[str] = Form(default=[]),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContentDetail:
    if len(tags) > 10:
        raise HTTPException(422, "too many tags (max 10)")

    try:
        info = validate_html_upload(
            filename=file.filename or "",
            content_type=file.content_type or "",
            stream=file.file,
            max_bytes=settings.upload_max_bytes,
        )
    except UploadValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    object_key = _build_object_key(datetime.utcnow())
    file.file.seek(0)
    try:
        await asyncio.to_thread(
            storage.put_object, object_key, file.file, "text/html"
        )
    except Exception as e:  # OSS 失败
        raise HTTPException(502, f"upload to storage failed: {e}") from e

    try:
        c = await cs.create_content(
            db,
            uploader_id=user.id,
            title=title,
            description=description,
            oss_bucket=settings.oss_bucket,
            oss_object_key=object_key,
            original_filename=file.filename or "untitled.html",
            content_type="text/html",
            size_bytes=info.size,
            sha256=info.sha256,
            tag_names=tags,
        )
        await write_audit(
            db, actor_id=user.id, action="content.create",
            target_type="content", target_id=c.id,
            detail={"size": info.size, "sha256": info.sha256},
        )
        await db.commit()
    except Exception:
        await asyncio.to_thread(storage.delete_object, object_key)
        raise

    summary = await cs.to_summary_dict(db, c)
    return ContentDetail(
        **summary,
        description=c.description,
        original_filename=c.original_filename,
        content_type=c.content_type,
        sha256=c.sha256,
        visibility=c.visibility,
        status=c.status,
    )
```

- [ ] **Step 2: 挂到 `app/main.py`**

```python
from app.api.contents import router as contents_router
...
app.include_router(contents_router)
```

- [ ] **Step 3: 测试 `tests/test_contents_upload_api.py`**

```python
import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    calls: list[str] = []

    def fake_put(key, data, ct):
        calls.append(key)
        return {"etag": "x", "request_id": "r"}

    def fake_del(key):
        calls.append(f"del:{key}")

    monkeypatch.setattr(oss_storage, "put_object", fake_put)
    monkeypatch.setattr(oss_storage, "delete_object", fake_del)
    return calls


@pytest.mark.asyncio
async def test_upload_creates_content(client, db, _stub_oss):
    await us.create_user(
        db,
        UserCreateIn(
            username="up1",
            password="Passw0rd!",
            role="creator",
        ),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": "up1", "password": "Passw0rd!"},
    )

    body = b"<!DOCTYPE html><html><body>hi</body></html>"
    r = await client.post(
        "/api/contents",
        data={"title": "T", "tags": ["a", "b"]},
        files={"file": ("a.html", body, "text/html")},
    )
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["title"] == "T"
    assert {t["name"] for t in j["tags"]} == {"a", "b"}
    assert _stub_oss and _stub_oss[0].startswith("contents/")


@pytest.mark.asyncio
async def test_upload_rejects_non_html(client, db):
    await us.create_user(
        db,
        UserCreateIn(
            username="up2",
            password="Passw0rd!",
            role="creator",
        ),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": "up2", "password": "Passw0rd!"},
    )
    r = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.pdf", b"%PDF-...", "application/pdf")},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_viewer_cannot_upload(client, db):
    await us.create_user(
        db,
        UserCreateIn(
            username="viewer1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": "viewer1", "password": "Passw0rd!"},
    )
    r = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.html", b"<html></html>", "text/html")},
    )
    assert r.status_code == 403
```

- [ ] **Step 4: 运行 + 提交**

Run: `pytest tests/test_contents_upload_api.py -v`
Expected: 3 passed。

```bash
git add app/api/contents.py app/main.py tests/test_contents_upload_api.py
git commit -m "feat(contents): upload endpoint with validation and OSS handoff"
```

---

### Task 9: 列表 / 详情 / 编辑 / 软删 API

**Files:**
- Modify: `app/api/contents.py`
- Create: `tests/test_contents_crud_api.py`

- [ ] **Step 1: 在 `app/api/contents.py` 追加路由**

```python
from fastapi import Query

from app.schemas.common import Page
from app.schemas.content import ContentSummary, ContentUpdateIn


@router.get("", response_model=Page[ContentSummary])
async def list_public(
    q: str | None = None,
    tag: str | None = None,
    order: str = Query(default="newest", pattern="^(newest|oldest)$"),
    page: int = 1,
    size: int = Query(default=24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[ContentSummary]:
    rows, total = await cs.list_public(
        db, q=q, tag=tag, order=order, page=page, size=size
    )
    items = [ContentSummary(**(await cs.to_summary_dict(db, r))) for r in rows]
    return Page[ContentSummary](
        items=items, total=total, page=page, size=size
    )


@router.get("/mine", response_model=Page[ContentSummary])
async def list_mine(
    q: str | None = None,
    tag: str | None = None,
    page: int = 1,
    size: int = 24,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("creator", "admin")),
) -> Page[ContentSummary]:
    rows, total = await cs.list_mine(
        db, user_id=user.id, q=q, tag=tag, page=page, size=size
    )
    items = [ContentSummary(**(await cs.to_summary_dict(db, r))) for r in rows]
    return Page[ContentSummary](
        items=items, total=total, page=page, size=size
    )


@router.get("/{content_id}", response_model=ContentDetail)
async def detail(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContentDetail:
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")
    summary = await cs.to_summary_dict(db, c)
    return ContentDetail(
        **summary,
        description=c.description,
        original_filename=c.original_filename,
        content_type=c.content_type,
        sha256=c.sha256,
        visibility=c.visibility,
        status=c.status,
    )


@router.patch("/{content_id}", response_model=ContentDetail)
async def patch_content(
    content_id: int,
    data: ContentUpdateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContentDetail:
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")
    if c.uploader_id != user.id and user.role != "admin":
        raise HTTPException(403, "forbidden")
    if data.tags is not None and len(data.tags) > 10:
        raise HTTPException(422, "too many tags")
    await cs.update_content(
        db,
        content=c,
        title=data.title,
        description=data.description,
        tags=data.tags,
    )
    await write_audit(
        db, actor_id=user.id, action="content.update",
        target_type="content", target_id=c.id,
    )
    await db.commit()
    summary = await cs.to_summary_dict(db, c)
    return ContentDetail(
        **summary,
        description=c.description,
        original_filename=c.original_filename,
        content_type=c.content_type,
        sha256=c.sha256,
        visibility=c.visibility,
        status=c.status,
    )


@router.delete("/{content_id}", status_code=204)
async def delete_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")
    if c.uploader_id != user.id and user.role != "admin":
        raise HTTPException(403, "forbidden")
    await cs.soft_delete(db, c)
    await write_audit(
        db, actor_id=user.id, action="content.delete",
        target_type="content", target_id=c.id,
    )
    await db.commit()
```

- [ ] **Step 2: 测试 `tests/test_contents_crud_api.py`**

```python
import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    monkeypatch.setattr(
        oss_storage,
        "put_object",
        lambda k, d, ct: {"etag": "x", "request_id": "r"},
    )
    monkeypatch.setattr(oss_storage, "delete_object", lambda k: None)


async def _login(client, db, name, role="creator"):
    await us.create_user(
        db,
        UserCreateIn(username=name, password="Passw0rd!", role=role),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": name, "password": "Passw0rd!"},
    )


async def _upload(client, title="T", tags=None):
    body = b"<!DOCTYPE html><html><body>x</body></html>"
    return await client.post(
        "/api/contents",
        data={"title": title, "tags": tags or []},
        files={"file": ("a.html", body, "text/html")},
    )


@pytest.mark.asyncio
async def test_list_detail_patch_delete(client, db):
    await _login(client, db, "x1")
    r = await _upload(client, "Foo", ["t1"])
    cid = r.json()["id"]

    lst = await client.get("/api/contents")
    assert lst.json()["total"] >= 1

    d = await client.get(f"/api/contents/{cid}")
    assert d.json()["title"] == "Foo"

    p = await client.patch(
        f"/api/contents/{cid}",
        json={"title": "Foo2", "tags": ["t2", "t3"]},
    )
    assert p.json()["title"] == "Foo2"
    assert {t["name"] for t in p.json()["tags"]} == {"t2", "t3"}

    rd = await client.delete(f"/api/contents/{cid}")
    assert rd.status_code == 204

    nf = await client.get(f"/api/contents/{cid}")
    assert nf.status_code == 404


@pytest.mark.asyncio
async def test_other_user_cannot_edit(client, db):
    await _login(client, db, "owner1")
    r = await _upload(client)
    cid = r.json()["id"]
    await client.post("/api/auth/logout")

    await _login(client, db, "stranger1")
    p = await client.patch(
        f"/api/contents/{cid}", json={"title": "hack"}
    )
    assert p.status_code == 403
```

- [ ] **Step 3: 运行 + 提交**

Run: `pytest tests/test_contents_crud_api.py -v`
Expected: 2 passed。

```bash
git add app/api/contents.py tests/test_contents_crud_api.py
git commit -m "feat(contents): list/detail/patch/soft-delete with RBAC"
```

---

### Task 10: 站内观看代理 `/view/{id}`

**Files:**
- Create: `app/api/view.py`
- Modify: `app/main.py`
- Create: `tests/test_view_proxy.py`

> 要点：
> - 仅登录用户可访问。
> - 流式回写、`Content-Type: text/html; charset=utf-8`、`X-Frame-Options` **不**设置（要允许同源 iframe），但严格 CSP `sandbox` 关键词使其在该响应内被强制沙箱化。
> - 同时落 `view_logs`。

- [ ] **Step 1: `app/api/view.py`**

```python
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.view_log import ViewLog
from app.oss import storage
from app.services import contents as cs

router = APIRouter(tags=["view"])

_HEADERS = {
    "Content-Security-Policy": "sandbox; default-src 'self' data:;",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "private, no-store",
}


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/view/{content_id}")
async def view_content(
    content_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")

    db.add(
        ViewLog(
            content_id=c.id,
            user_id=user.id,
            client_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent", "")[:255],
        )
    )
    await db.commit()

    def _gen():
        yield from storage.stream_object(c.oss_object_key)

    async def _aiter():
        loop = asyncio.get_running_loop()
        it = await loop.run_in_executor(None, _gen)
        # _gen 是同步生成器；为简化，先把整体读入内存（v1 文件 ≤ 10MB 可接受）。
        chunks: list[bytes] = []
        for chunk in it:
            chunks.append(chunk)
        for c2 in chunks:
            yield c2

    return StreamingResponse(
        _aiter(), media_type="text/html; charset=utf-8", headers=_HEADERS
    )
```

> 设计取舍：v1 内容 ≤ 10MB，先一次性读入再流回，省去同步生成器到异步的复杂转换。

- [ ] **Step 2: 挂到 `app/main.py`**

```python
from app.api.view import router as view_router
...
app.include_router(view_router)
```

- [ ] **Step 3: 测试 `tests/test_view_proxy.py`**

```python
import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    stored: dict[str, bytes] = {}

    def fake_put(key, data, ct):
        stored[key] = data.read()
        return {"etag": "x", "request_id": "r"}

    def fake_stream(key):
        yield stored[key]

    monkeypatch.setattr(oss_storage, "put_object", fake_put)
    monkeypatch.setattr(oss_storage, "stream_object", fake_stream)
    monkeypatch.setattr(oss_storage, "delete_object", lambda k: None)
    return stored


@pytest.mark.asyncio
async def test_view_returns_html_with_csp(client, db, _stub_oss):
    await us.create_user(
        db,
        UserCreateIn(
            username="vc1",
            password="Passw0rd!",
            role="creator",
        ),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": "vc1", "password": "Passw0rd!"},
    )
    body = b"<!DOCTYPE html><html><body>HELLO</body></html>"
    up = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.html", body, "text/html")},
    )
    cid = up.json()["id"]

    r = await client.get(f"/view/{cid}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "sandbox" in r.headers["content-security-policy"]
    assert b"HELLO" in r.content


@pytest.mark.asyncio
async def test_view_requires_login(client):
    r = await client.get("/view/1")
    assert r.status_code == 401
```

- [ ] **Step 4: 运行 + 提交**

Run: `pytest tests/test_view_proxy.py -v`
Expected: 2 passed。

```bash
git add app/api/view.py app/main.py tests/test_view_proxy.py
git commit -m "feat(view): authenticated /view/{id} proxy with CSP sandbox"
```

---

### Task 11: 公开标签接口 `/api/tags`

**Files:**
- Create: `app/api/tags.py`
- Modify: `app/main.py`
- Create: `tests/test_tags_api.py`

- [ ] **Step 1: `app/api/tags.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.tag import TagOut
from app.services import tags as svc

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
async def list_tags(
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TagOut]:
    rows = await svc.list_all(db, q=q)
    return [TagOut.model_validate(t) for t in rows]
```

- [ ] **Step 2: 挂到 `app/main.py`**

```python
from app.api.tags import router as tags_router
...
app.include_router(tags_router)
```

- [ ] **Step 3: 测试**

```python
import pytest

from app.schemas.user import UserCreateIn
from app.services import tags as ts
from app.services import users as us


@pytest.mark.asyncio
async def test_list_tags(client, db):
    await us.create_user(
        db,
        UserCreateIn(
            username="tg1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    await ts.get_or_create_many(db, ["α", "β", "γ"])
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": "tg1", "password": "Passw0rd!"},
    )

    r = await client.get("/api/tags?q=α")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "α" in names
```

- [ ] **Step 4: 运行 + 提交**

Run: `pytest tests/test_tags_api.py -v`
Expected: 1 passed。

```bash
git add app/api/tags.py app/main.py tests/test_tags_api.py
git commit -m "feat(tags): public list endpoint"
```

---

### Task 12: 管理员标签 API `/api/admin/tags`

**Files:**
- Create: `app/api/admin_tags.py`
- Modify: `app/main.py`
- Create: `tests/test_admin_tags_api.py`

- [ ] **Step 1: `app/api/admin_tags.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.user import User
from app.schemas.tag import (
    TagAdminOut,
    TagCreateIn,
    TagMergeIn,
    TagOut,
    TagRenameIn,
)
from app.services import tags as svc
from app.services.audit import write_audit

router = APIRouter(
    prefix="/api/admin/tags",
    tags=["admin-tags"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=list[TagAdminOut])
async def list_(
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
):
    rows = await svc.list_admin(db, q=q)
    return [
        TagAdminOut(
            id=t.id,
            name=t.name,
            content_count=cnt,
            created_at=t.created_at.isoformat(),
        )
        for t, cnt in rows
    ]


@router.post("", response_model=TagOut, status_code=201)
async def create_(
    data: TagCreateIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
):
    [t] = await svc.get_or_create_many(db, [data.name])
    await write_audit(
        db, actor_id=actor.id, action="tag.create",
        target_type="tag", target_id=t.id,
        detail={"name": t.name},
    )
    await db.commit()
    return TagOut.model_validate(t)


@router.patch("/{tag_id}", response_model=TagOut)
async def rename_(
    tag_id: int,
    data: TagRenameIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
):
    try:
        t = await svc.rename(db, tag_id, data.name.strip())
    except LookupError:
        raise HTTPException(404, "tag not found")
    except ValueError:
        raise HTTPException(409, "name taken")
    await write_audit(
        db, actor_id=actor.id, action="tag.rename",
        target_type="tag", target_id=tag_id,
        detail={"name": data.name},
    )
    await db.commit()
    return TagOut.model_validate(t)


@router.delete("/{tag_id}", status_code=204)
async def delete_(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
):
    try:
        await svc.delete_unused(db, tag_id)
    except ValueError:
        raise HTTPException(409, "tag in use")
    await write_audit(
        db, actor_id=actor.id, action="tag.delete",
        target_type="tag", target_id=tag_id,
    )
    await db.commit()


@router.post("/{tag_id}/merge", response_model=dict)
async def merge_(
    tag_id: int,
    data: TagMergeIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
):
    try:
        affected = await svc.merge(db, tag_id, data.target_id)
    except LookupError:
        raise HTTPException(404, "tag not found")
    except ValueError as e:
        raise HTTPException(409, str(e))
    await write_audit(
        db, actor_id=actor.id, action="tag.merge",
        target_type="tag", target_id=tag_id,
        detail={"target_id": data.target_id, "affected": affected},
    )
    await db.commit()
    return {"affected": affected}
```

- [ ] **Step 2: 挂到 `app/main.py`**

```python
from app.api.admin_tags import router as admin_tags_router
...
app.include_router(admin_tags_router)
```

- [ ] **Step 3: 测试 `tests/test_admin_tags_api.py`**

```python
import pytest

from app.schemas.user import UserCreateIn
from app.services import users as us


async def _admin(client, db, name="adm-tag1"):
    await us.create_user(
        db,
        UserCreateIn(username=name, password="Passw0rd!", role="admin"),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": name, "password": "Passw0rd!"},
    )


@pytest.mark.asyncio
async def test_create_rename_delete_merge(client, db):
    await _admin(client, db)
    r = await client.post("/api/admin/tags", json={"name": "alpha"})
    a_id = r.json()["id"]
    r2 = await client.post("/api/admin/tags", json={"name": "beta"})
    b_id = r2.json()["id"]

    rn = await client.patch(
        f"/api/admin/tags/{a_id}", json={"name": "alpha2"}
    )
    assert rn.json()["name"] == "alpha2"

    mg = await client.post(
        f"/api/admin/tags/{a_id}/merge", json={"target_id": b_id}
    )
    assert mg.status_code == 200

    # alpha2 should be gone
    lst = await client.get("/api/admin/tags")
    names = [t["name"] for t in lst.json()]
    assert "alpha2" not in names
```

- [ ] **Step 4: 运行 + 提交**

Run: `pytest tests/test_admin_tags_api.py -v`
Expected: 1 passed。

```bash
git add app/api/admin_tags.py app/main.py tests/test_admin_tags_api.py
git commit -m "feat(admin): tag management endpoints"
```

---

### Task 13: 管理员全部内容（含已删除）

**Files:**
- Modify: `app/api/contents.py`（追加 admin 路由）
- Create: `tests/test_admin_contents_api.py`

- [ ] **Step 1: 在 `app/api/contents.py` 加路由**

```python
from app.deps import require_role  # 已存在导入即可


@router.get(
    "/admin/all",
    response_model=Page[ContentSummary],
    dependencies=[Depends(require_role("admin"))],
)
async def admin_list(
    q: str | None = None,
    tag: str | None = None,
    status_: str | None = Query(default=None, alias="status"),
    page: int = 1,
    size: int = 24,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> Page[ContentSummary]:
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from app.models.content import Content
    from app.models.tag import ContentTag, Tag

    base = select(Content).options(selectinload(Content.tags))
    cnt = select(func.count(Content.id))
    if q:
        base = base.where(Content.title.ilike(f"%{q}%"))
        cnt = cnt.where(Content.title.ilike(f"%{q}%"))
    if tag:
        sub = select(ContentTag.content_id).join(
            Tag, Tag.id == ContentTag.tag_id
        ).where(Tag.name == tag)
        base = base.where(Content.id.in_(sub))
        cnt = cnt.where(Content.id.in_(sub))
    if status_:
        base = base.where(Content.status == status_)
        cnt = cnt.where(Content.status == status_)
    base = base.order_by(Content.created_at.desc()).offset(
        (page - 1) * size
    ).limit(size)
    rows = (await db.execute(base)).scalars().all()
    total = (await db.execute(cnt)).scalar_one()
    items = [
        ContentSummary(**(await cs.to_summary_dict(db, r))) for r in rows
    ]
    return Page[ContentSummary](
        items=items, total=total, page=page, size=size
    )


@router.post(
    "/{content_id}/restore",
    response_model=ContentDetail,
    dependencies=[Depends(require_role("admin"))],
)
async def restore(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> ContentDetail:
    from app.models.content import Content
    c = await db.get(Content, content_id)
    if not c:
        raise HTTPException(404, "content not found")
    c.status = "active"
    await write_audit(
        db, actor_id=actor.id, action="content.restore",
        target_type="content", target_id=c.id,
    )
    await db.commit()
    summary = await cs.to_summary_dict(db, c)
    return ContentDetail(
        **summary,
        description=c.description,
        original_filename=c.original_filename,
        content_type=c.content_type,
        sha256=c.sha256,
        visibility=c.visibility,
        status=c.status,
    )
```

- [ ] **Step 2: 测试**

```python
import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    monkeypatch.setattr(
        oss_storage, "put_object",
        lambda k, d, ct: {"etag": "x", "request_id": "r"},
    )


async def _login(client, db, name, role):
    await us.create_user(
        db,
        UserCreateIn(username=name, password="Passw0rd!", role=role),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": name, "password": "Passw0rd!"},
    )


@pytest.mark.asyncio
async def test_admin_all_includes_deleted_and_restore(client, db):
    await _login(client, db, "admA", "admin")
    body = b"<!DOCTYPE html><html><body>x</body></html>"
    up = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.html", body, "text/html")},
    )
    cid = up.json()["id"]
    await client.delete(f"/api/contents/{cid}")

    r = await client.get("/api/contents/admin/all?status=deleted")
    assert any(it["id"] == cid for it in r.json()["items"])

    rs = await client.post(f"/api/contents/{cid}/restore")
    assert rs.json()["status"] == "active"
```

- [ ] **Step 3: 运行 + 提交**

Run: `pytest tests/test_admin_contents_api.py -v`
Expected: 1 passed。

```bash
git add app/api/contents.py tests/test_admin_contents_api.py
git commit -m "feat(admin): list-all and restore for contents"
```

---

### Task 14: README 与路由清单更新

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 在 "路由概览" 章节追加**

```markdown
- `POST /api/contents`（creator/admin，multipart 上传）
- `GET  /api/contents`（公开库）
- `GET  /api/contents/mine`（creator/admin）
- `GET  /api/contents/{id}` / `PATCH` / `DELETE`
- `GET  /view/{id}`（沙箱观看）
- `GET  /api/tags`
- `GET/POST/PATCH/DELETE /api/admin/tags` + `POST /api/admin/tags/{id}/merge`
- `GET  /api/contents/admin/all` / `POST /api/contents/{id}/restore`（admin）
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: enumerate content/tag/view routes"
```

---

## Self-Review 结果

- 覆盖范围：设计 §3.1/3.2、§4 全部新表、§5.2、§5.6、§6.1（CSP/sandbox 头在 view.py 实现）、§6.3 上传校验、§6.4 OSS 私有读 + 后端代理 + uuid object key（无用户名）。
- 不含：§3.3/3.4 分发链接（plan 3）；§5.3/5.4 share 端点（plan 3）；§5.5 admin user（plan 1 已完成）。
- 命名一致：`get_active`、`list_public`、`to_summary_dict` 在 service 与 api 一致；`storage.put_object/stream_object/delete_object` 在 stub 和真实路径一致。
- 无占位符；测试均含完整代码。
- 取舍：view 把整体读入再回传，避免同步生成器到异步流的复杂转换；v1 文件 ≤10MB，可接受。Plan 5 部署阶段如需大文件再换真正的流式实现。

---

## 交付清单

- 上传 HTML → OSS（stub 验证）+ DB 事务安全（失败回滚 OSS）。
- 公开库列表（标签/搜索/排序/分页）、详情、编辑、软删、权限边界正确。
- `/view/{id}` 返回沙箱头的 HTML，`view_logs` 有记录。
- 标签 CRUD + merge + 重命名。
- admin 可看全部内容（含已删除）+ 恢复。
- `pytest` 全绿。
