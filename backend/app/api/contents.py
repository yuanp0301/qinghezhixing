import asyncio
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.oss import storage
from app.schemas.common import Page
from app.schemas.content import ContentDetail, ContentSummary, ContentUpdateIn
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
    except Exception as e:
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

    # Reload with tags eagerly loaded (post-commit attributes are expired).
    c = await cs.get_active(db, c.id)
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
    rows, total = await cs.list_public(db, q=q, tag=tag, order=order, page=page, size=size)
    items = [ContentSummary(**(await cs.to_summary_dict(db, r))) for r in rows]
    return Page[ContentSummary](items=items, total=total, page=page, size=size)


@router.get("/mine", response_model=Page[ContentSummary])
async def list_mine(
    q: str | None = None,
    tag: str | None = None,
    page: int = 1,
    size: int = 24,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("creator", "admin")),
) -> Page[ContentSummary]:
    rows, total = await cs.list_mine(db, user_id=user.id, q=q, tag=tag, page=page, size=size)
    items = [ContentSummary(**(await cs.to_summary_dict(db, r))) for r in rows]
    return Page[ContentSummary](items=items, total=total, page=page, size=size)


@router.get("/{content_id:int}", response_model=ContentDetail)
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


@router.patch("/{content_id:int}", response_model=ContentDetail)
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
        db, content=c, title=data.title, description=data.description, tags=data.tags,
    )
    await write_audit(db, actor_id=user.id, action="content.update", target_type="content", target_id=c.id)
    await db.commit()
    c = await cs.get_active(db, c.id)
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


@router.delete("/{content_id:int}", status_code=204)
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
    await write_audit(db, actor_id=user.id, action="content.delete", target_type="content", target_id=c.id)
    await db.commit()


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
    base = base.order_by(Content.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(base)).scalars().all()
    total = (await db.execute(cnt)).scalar_one()
    items = [ContentSummary(**(await cs.to_summary_dict(db, r))) for r in rows]
    return Page[ContentSummary](items=items, total=total, page=page, size=size)


@router.post(
    "/{content_id:int}/restore",
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
    # Reload with tags eagerly loaded for summary serialization
    c = await cs.get_active(db, c.id)
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
