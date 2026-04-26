import secrets
import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.content import Content
from app.models.share_key import ShareKey
from app.models.share_link import ShareLink


_settings = get_settings()


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
    key_user_info: str,
    expires_in_seconds: int,
    allow_download: bool,
) -> ShareLink:
    token = _build_token(key_user_info)
    sl = ShareLink(
        token=token,
        content_id=content.id,
        created_by=creator_id,
        expires_at=_now() + timedelta(seconds=expires_in_seconds),
        allow_download=allow_download,
    )
    db.add(sl)
    db.add(
        ShareKey(
            user_id=creator_id,
            user_info=key_user_info,
            key=token,
            is_used=False,
        )
    )
    await db.flush()
    return sl


def _build_token(username: str) -> str:
    nonce = secrets.token_urlsafe(12)
    payload = f"{username}:{nonce}:{int(_now().timestamp())}".encode("utf-8")
    digest = hmac.new(
        _settings.app_secret_key.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


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
    sl = await get_by_token(db, token)
    if not sl:
        return ValidationResult(state="not_found")
    s = state_of(sl)
    if s == "active":
        return ValidationResult(state="valid", share=sl)
    return ValidationResult(state=s, share=sl)


async def mark_key_used(
    db: AsyncSession, *, token: str, use_mode: str
) -> None:
    if use_mode not in {"preview", "download"}:
        return
    stmt = select(ShareKey).where(ShareKey.key == token)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        return
    if row.is_used:
        return
    row.is_used = True
    row.used_at = _now()
    row.use_mode = use_mode
    await db.flush()
