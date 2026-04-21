import pytest

from app.schemas.user import UserCreateIn
from app.services import contents as cs
from app.services import users as us


@pytest.mark.asyncio
async def test_create_and_query(db):
    u = await us.create_user(
        db,
        UserCreateIn(
            username="creator9",
            password="Passw0rd!",
            role="creator",
        ),
    )
    c = await cs.create_content(
        db,
        uploader_id=u.id,
        title="Hello",
        description=None,
        oss_bucket="b",
        oss_object_key="contents/2026/04/abc.html",
        original_filename="hello.html",
        content_type="text/html",
        size_bytes=10,
        sha256="0" * 64,
        tag_names=["演示", "Demo"],
    )
    assert c.id

    rows, total = await cs.list_public(
        db, q=None, tag="演示", order="newest", page=1, size=10
    )
    assert total == 1
    assert rows[0].id == c.id


@pytest.mark.asyncio
async def test_update_and_soft_delete(db):
    u = await us.create_user(
        db,
        UserCreateIn(
            username="creatorA",
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
        oss_object_key="contents/x.html",
        original_filename="x.html",
        content_type="text/html",
        size_bytes=1,
        sha256="0" * 64,
        tag_names=[],
    )
    await cs.update_content(
        db, content=c, title="t2", description="d", tags=["A"]
    )
    assert c.title == "t2"
    assert {t.name for t in c.tags} == {"A"}

    await cs.soft_delete(db, c)
    assert await cs.get_active(db, c.id) is None
