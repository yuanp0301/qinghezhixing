import pytest

from app.services import tags as svc


@pytest.mark.asyncio
async def test_get_or_create_dedupes(db):
    a = await svc.get_or_create_many(db, ["x", "y", "x"])
    assert {t.name for t in a} == {"x", "y"}
    b = await svc.get_or_create_many(db, ["x", "z"])
    names = {t.name for t in b}
    assert names == {"x", "z"}


@pytest.mark.asyncio
async def test_rename_and_delete(db):
    [t] = await svc.get_or_create_many(db, ["foo"])
    r = await svc.rename(db, t.id, "foo2")
    assert r.name == "foo2"
    await svc.delete_unused(db, t.id)
