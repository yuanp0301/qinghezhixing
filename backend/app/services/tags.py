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
