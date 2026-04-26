from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionLocal
from app.models.user import User
from app.security.sessions import get_session, touch_session

settings = get_settings()


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s


async def get_current_user(
    qh_session: Annotated[str | None, Cookie(alias="qh_session")] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not qh_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    data = await get_session(db, qh_session)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session expired")
    user = await db.get(User, data["user_id"])
    if not user or user.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user inactive")
    await touch_session(db, qh_session, settings.session_ttl_seconds)
    return user


def require_role(*roles: str):
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        return user

    return _dep
