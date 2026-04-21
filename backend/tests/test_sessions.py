import pytest

from app.security.sessions import (
    create_session,
    get_session,
    delete_session,
)


@pytest.mark.asyncio
async def test_session_roundtrip():
    sid = await create_session(user_id=42, ttl_seconds=60)
    assert sid and len(sid) >= 32
    data = await get_session(sid)
    assert data == {"user_id": 42}
    await delete_session(sid)
    assert await get_session(sid) is None


@pytest.mark.asyncio
async def test_missing_session_returns_none():
    assert await get_session("nope") is None
