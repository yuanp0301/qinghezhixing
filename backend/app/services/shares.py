import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.models.share_link import ShareLink


TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{22,64}$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def state_of(sl: ShareLink, now: datetime | None = None) -> str:
    t = now or _now()
    if sl.revoked_at is not None:
        return "revoked"
    if sl.expires_at <= t:
        return "expired"
    return "active"


async def create_share(
    db: AsyncSession,
    *,
    content: Content,
    creator_id: int,
    expires_in_seconds: int,
    allow_download: bool,
) -> ShareLink:
    token = secrets.token_urlsafe(22)
    sl = ShareLink(
        token=token,
        content_id=content.id,
        created_by=creator_id,
        expires_at=_now() + timedelta(seconds=expires_in_seconds),
        allow_download=allow_download,
    )
    db.add(sl)
    await db.flush()
    return sl


async def revoke(db: AsyncSession, sl: ShareLink) -> ShareLink:
    if sl.revoked_at is None:
        sl.revoked_at = _now()
        await db.flush()
    return sl


async def list_for_content(
    db: AsyncSession, *, content_id: int
) -> Sequence[ShareLink]:
    stmt = (
        select(ShareLink)
        .where(ShareLink.content_id == content_id)
        .order_by(ShareLink.created_at.desc())
    )
    return (await db.execute(stmt)).scalars().all()


async def get_by_token(
    db: AsyncSession, token: str
) -> ShareLink | None:
    stmt = select(ShareLink).where(ShareLink.token == token)
    return (await db.execute(stmt)).scalar_one_or_none()


async def count_access(
    db: AsyncSession, token: str
) -> int:
    from app.models.share_access_log import ShareAccessLog

    stmt = select(func.count(ShareAccessLog.id)).where(
        ShareAccessLog.token == token,
        ShareAccessLog.result == "success",
    )
    return (await db.execute(stmt)).scalar_one()


@dataclass
class ValidationResult:
    state: str  # valid | expired | revoked | not_found
    share: ShareLink | None = None


async def validate_token(
    db: AsyncSession, token: str
) -> ValidationResult:
    if not TOKEN_RE.match(token):
        return ValidationResult(state="not_found")
    sl = await get_by_token(db, token)
    if not sl:
        return ValidationResult(state="not_found")
    s = state_of(sl)
    if s == "active":
        return ValidationResult(state="valid", share=sl)
    return ValidationResult(state=s, share=sl)
