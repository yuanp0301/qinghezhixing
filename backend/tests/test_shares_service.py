from datetime import datetime, timedelta, timezone

import pytest

from app.models.share_link import ShareLink
from app.schemas.user import UserCreateIn
from app.services import shares as ss
from app.services import contents as cs
from app.services import users as us


async def _seed(db):
    u = await us.create_user(
        db,
        UserCreateIn(
            username=f"u_{int(datetime.now().timestamp() * 1000)}",
            password="Passw0rd!",
            role="creator",
        ),
    )
    c = await cs.create_content(
        db,
        uploader_id=u.id,
        title="t",
        description=None,
        oss_bucket="b",
        oss_object_key="k",
        original_filename="x.html",
        content_type="text/html",
        size_bytes=1,
        sha256="0" * 64,
        tag_names=[],
    )
    return u, c


@pytest.mark.asyncio
async def test_create_and_state(db):
    u, c = await _seed(db)
    sl = await ss.create_share(
        db,
        content=c,
        creator_id=u.id,
        expires_in_seconds=60,
        allow_download=False,
    )
    assert len(sl.token) >= 22
    assert ss.state_of(sl) == "active"


@pytest.mark.asyncio
async def test_revoke(db):
    u, c = await _seed(db)
    sl = await ss.create_share(
        db, content=c, creator_id=u.id, expires_in_seconds=60,
        allow_download=False,
    )
    await ss.revoke(db, sl)
    assert ss.state_of(sl) == "revoked"


@pytest.mark.asyncio
async def test_validate_token(db):
    u, c = await _seed(db)
    sl = await ss.create_share(
        db, content=c, creator_id=u.id, expires_in_seconds=60,
        allow_download=False,
    )
    ok = await ss.validate_token(db, sl.token)
    assert ok.state == "valid"
    assert ok.share.id == sl.id


@pytest.mark.asyncio
async def test_validate_expired(db):
    u, c = await _seed(db)
    sl = ShareLink(
        token="x" * 22,
        content_id=c.id,
        created_by=u.id,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        allow_download=False,
    )
    db.add(sl)
    await db.flush()
    v = await ss.validate_token(db, sl.token)
    assert v.state == "expired"


@pytest.mark.asyncio
async def test_validate_revoked(db):
    u, c = await _seed(db)
    sl = await ss.create_share(
        db, content=c, creator_id=u.id, expires_in_seconds=60,
        allow_download=False,
    )
    await ss.revoke(db, sl)
    v = await ss.validate_token(db, sl.token)
    assert v.state == "revoked"


@pytest.mark.asyncio
async def test_validate_not_found(db):
    v = await ss.validate_token(db, "zzzz" * 6)
    assert v.state == "not_found"


@pytest.mark.asyncio
async def test_validate_bad_format(db):
    v = await ss.validate_token(db, "bad")
    assert v.state == "not_found"
