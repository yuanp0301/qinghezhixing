import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_session(db: AsyncSession, user_id: int, ttl_seconds: int) -> str:
    sid = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            sid=sid,
            user_id=user_id,
            expires_at=_now() + timedelta(seconds=ttl_seconds),
        )
    )
    await db.flush()
    return sid


async def get_session(db: AsyncSession, sid: str) -> dict | None:
    row = (
        await db.execute(
            select(UserSession).where(
                UserSession.sid == sid,
                UserSession.expires_at > _now(),
            )
        )
    ).scalar_one_or_none()
    return {"user_id": row.user_id} if row else None


async def delete_session(db: AsyncSession, sid: str) -> None:
    await db.execute(delete(UserSession).where(UserSession.sid == sid))
    await db.flush()


async def touch_session(db: AsyncSession, sid: str, ttl_seconds: int) -> None:
    row = (
        await db.execute(select(UserSession).where(UserSession.sid == sid))
    ).scalar_one_or_none()
    if not row:
        return
    now = _now()
    row.expires_at = now + timedelta(seconds=ttl_seconds)
    row.updated_at = now
    await db.flush()
