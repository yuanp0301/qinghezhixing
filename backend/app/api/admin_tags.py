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
