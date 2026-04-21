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
    await db.refresh(content, attribute_names=["tags"])
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
