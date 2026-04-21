import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    monkeypatch.setattr(
        oss_storage, "put_object",
        lambda k, d, ct: {"etag": "x", "request_id": "r"},
    )
    monkeypatch.setattr(oss_storage, "delete_object", lambda k: None)


async def _login(client, db, name, role="creator"):
    await us.create_user(
        db,
        UserCreateIn(username=name, password="Passw0rd!", role=role),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": name, "password": "Passw0rd!"},
    )


async def _upload(client):
    body = b"<!DOCTYPE html><html><body>x</body></html>"
    r = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.html", body, "text/html")},
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_and_list_shares(client, db):
    await _login(client, db, "sh_owner1")
    cid = await _upload(client)

    r = await client.post(
        f"/api/contents/{cid}/shares",
        json={"expires_in_seconds": 3600, "allow_download": True},
    )
    assert r.status_code == 201
    j = r.json()
    assert j["state"] == "active"
    assert j["url"].endswith(f"/s/{j['token']}")

    lst = await client.get(f"/api/contents/{cid}/shares")
    assert lst.status_code == 200
    assert len(lst.json()) == 1


@pytest.mark.asyncio
async def test_stranger_cannot_create(client, db):
    await _login(client, db, "sh_owner2")
    cid = await _upload(client)
    await client.post("/api/auth/logout")

    await _login(client, db, "sh_stranger2")
    r = await client.post(
        f"/api/contents/{cid}/shares",
        json={"expires_in_seconds": 3600},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_revoke(client, db):
    await _login(client, db, "sh_owner3")
    cid = await _upload(client)
    r = await client.post(
        f"/api/contents/{cid}/shares",
        json={"expires_in_seconds": 3600},
    )
    token = r.json()["token"]
    d = await client.delete(f"/api/shares/{token}")
    assert d.status_code == 204

    lst = await client.get(f"/api/contents/{cid}/shares")
    assert lst.json()[0]["state"] == "revoked"
