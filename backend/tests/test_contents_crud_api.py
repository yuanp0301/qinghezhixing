import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    monkeypatch.setattr(oss_storage, "put_object", lambda k, d, ct: {"etag": "x", "request_id": "r"})
    monkeypatch.setattr(oss_storage, "delete_object", lambda k: None)


async def _login(client, db, name, role="creator"):
    await us.create_user(db, UserCreateIn(username=name, password="Passw0rd!", role=role))
    await db.commit()
    await client.post("/api/auth/login", json={"username": name, "password": "Passw0rd!"})


async def _upload(client, title="T", tags=None):
    body = b"<!DOCTYPE html><html><body>x</body></html>"
    return await client.post(
        "/api/contents",
        data={"title": title, "tags": tags or []},
        files={"file": ("a.html", body, "text/html")},
    )


@pytest.mark.asyncio
async def test_list_detail_patch_delete(client, db):
    await _login(client, db, "x1")
    r = await _upload(client, "Foo", ["t1"])
    cid = r.json()["id"]

    lst = await client.get("/api/contents")
    assert lst.json()["total"] >= 1

    d = await client.get(f"/api/contents/{cid}")
    assert d.json()["title"] == "Foo"

    p = await client.patch(f"/api/contents/{cid}", json={"title": "Foo2", "tags": ["t2", "t3"]})
    assert p.json()["title"] == "Foo2"
    assert {t["name"] for t in p.json()["tags"]} == {"t2", "t3"}

    rd = await client.delete(f"/api/contents/{cid}")
    assert rd.status_code == 204

    nf = await client.get(f"/api/contents/{cid}")
    assert nf.status_code == 404


@pytest.mark.asyncio
async def test_other_user_cannot_edit(client, db):
    await _login(client, db, "owner1")
    r = await _upload(client)
    cid = r.json()["id"]
    await client.post("/api/auth/logout")

    await _login(client, db, "stranger1")
    p = await client.patch(f"/api/contents/{cid}", json={"title": "hack"})
    assert p.status_code == 403
