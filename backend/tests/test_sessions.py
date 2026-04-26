import pytest
from sqlalchemy import text

from app.security.sessions import (
    create_session,
    get_session,
    delete_session,
)


@pytest.mark.asyncio
async def test_session_roundtrip(db):
    await db.execute(
        text(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES (42, 'u42', 'x', 'viewer')"
        )
    )
    await db.flush()
    sid = await create_session(db, user_id=42, ttl_seconds=60)
    assert sid and len(sid) >= 32
    data = await get_session(db, sid)
    assert data == {"user_id": 42}
    await delete_session(db, sid)
    assert await get_session(db, sid) is None


@pytest.mark.asyncio
async def test_missing_session_returns_none(db):
    assert await get_session(db, "nope") is None
