from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_db
from app.models.share_access_log import ShareAccessLog
from app.models.share_key import ShareKey
from app.models.share_link import ShareLink
from app.models.share_usage_event import ShareUsageEvent
from app.models.user import User
from app.schemas.common import Page
from app.schemas.share import (
    OfflineOpenOut,
    ShareAccessOut,
    ShareCreateIn,
    ShareKeyOut,
    ShareOut,
)
from app.services import contents as cs
from app.services import share_access as sa
from app.services import shares as ss
from app.services.audit import write_audit

settings = get_settings()
router = APIRouter(tags=["shares"])


def _to_out(sl) -> ShareOut:
    return ShareOut(
        token=sl.token,
        url=f"{settings.public_base_url}/s/{sl.token}",
        content_id=sl.content_id,
        created_by=sl.created_by,
        created_at=sl.created_at,
        expires_at=sl.expires_at,
        revoked_at=sl.revoked_at,
        allow_download=sl.allow_download,
        state=ss.state_of(sl),
    )


@router.post(
    "/api/contents/{content_id}/shares",
    response_model=ShareOut,
    status_code=201,
)
async def create_share(
    content_id: int,
    data: ShareCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShareOut:
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")
    if c.uploader_id != user.id and user.role != "admin":
        raise HTTPException(403, "forbidden")
    if not (
        settings.share_min_seconds
        <= data.expires_in_seconds
        <= settings.share_max_seconds
    ):
        raise HTTPException(422, "expires_in_seconds out of range")
    key_user_info = data.user_info.strip()
    if not key_user_info:
        raise HTTPException(422, "user_info is required")

    sl = await ss.create_share(
        db,
        content=c,
        creator_id=user.id,
        key_user_info=key_user_info,
        expires_in_seconds=data.expires_in_seconds,
        allow_download=data.allow_download,
    )
    await write_audit(
        db, actor_id=user.id, action="share.create",
        target_type="share", target_id=sl.id,
        detail={"content_id": c.id, "expires_in": data.expires_in_seconds},
    )
    await db.commit()
    await db.refresh(sl)
    return _to_out(sl)


@router.get(
    "/api/contents/{content_id}/shares",
    response_model=list[ShareOut],
)
async def list_shares(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ShareOut]:
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")
    if c.uploader_id != user.id and user.role != "admin":
        raise HTTPException(403, "forbidden")
    rows = await ss.list_for_content(db, content_id=content_id)
    return [_to_out(r) for r in rows]


@router.delete("/api/shares/{token}", status_code=204)
async def revoke_share(
    token: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    sl = await ss.get_by_token(db, token)
    if not sl:
        raise HTTPException(404, "not found")
    if sl.created_by != user.id and user.role != "admin":
        raise HTTPException(403, "forbidden")
    await ss.revoke(db, sl)
    await write_audit(
        db, actor_id=user.id, action="share.revoke",
        target_type="share", target_id=sl.id,
    )
    await db.commit()


@router.get(
    "/api/shares/{token}/logs",
    response_model=Page[ShareAccessOut],
)
async def share_logs(
    token: str,
    page: int = 1,
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[ShareAccessOut]:
    sl = await ss.get_by_token(db, token)
    if not sl:
        raise HTTPException(404, "not found")
    if sl.created_by != user.id and user.role != "admin":
        raise HTTPException(403, "forbidden")

    stmt = (
        select(ShareAccessLog)
        .where(ShareAccessLog.token == token)
        .order_by(ShareAccessLog.viewed_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    cnt_stmt = select(func.count(ShareAccessLog.id)).where(
        ShareAccessLog.token == token
    )
    rows = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(cnt_stmt)).scalar_one()

    items = [
        ShareAccessOut(
            viewed_at=r.viewed_at,
            client_ip_masked=sa.mask_ip(r.client_ip),
            user_agent=r.user_agent,
            result=r.result,
        )
        for r in rows
    ]
    return Page[ShareAccessOut](
        items=items, total=total, page=page, size=size
    )


@router.get(
    "/api/contents/{content_id}/share-keys",
    response_model=list[ShareKeyOut],
)
async def list_share_keys(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ShareKeyOut]:
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")
    if c.uploader_id != user.id and user.role != "admin":
        raise HTTPException(403, "forbidden")

    stmt = (
        select(ShareKey)
        .join(ShareLink, ShareLink.token == ShareKey.key)
        .where(ShareLink.content_id == content_id)
        .order_by(ShareKey.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        ShareKeyOut(
            key=r.key,
            user_id=r.user_id,
            user_info=r.user_info,
            is_used=r.is_used,
            used_at=r.used_at,
            use_mode=r.use_mode,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get(
    "/api/contents/{content_id}/offline-opens",
    response_model=Page[OfflineOpenOut],
)
async def list_offline_opens(
    content_id: int,
    page: int = 1,
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[OfflineOpenOut]:
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")
    if c.uploader_id != user.id and user.role != "admin":
        raise HTTPException(403, "forbidden")

    stmt = (
        select(ShareUsageEvent)
        .where(ShareUsageEvent.content_id == content_id)
        .order_by(ShareUsageEvent.reported_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    cnt_stmt = select(func.count(ShareUsageEvent.id)).where(
        ShareUsageEvent.content_id == content_id
    )
    rows = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(cnt_stmt)).scalar_one()
    items = [
        OfflineOpenOut(
            token=r.token,
            user_info=r.user_info,
            opened_at=r.opened_at,
            reported_at=r.reported_at,
            is_offline_replay=r.is_offline_replay,
            user_agent=r.user_agent,
        )
        for r in rows
    ]
    return Page[OfflineOpenOut](items=items, total=total, page=page, size=size)
