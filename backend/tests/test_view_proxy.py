import io

import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    stored: dict[str, bytes] = {}

    def fake_put(key, data, ct):
        stored[key] = data.read() if hasattr(data, "read") else bytes(data)
        return {"etag": "x", "request_id": "r"}

    def fake_stream(key):
        yield stored[key]

    monkeypatch.setattr(oss_storage, "put_object", fake_put)
    monkeypatch.setattr(oss_storage, "stream_object", fake_stream)
    monkeypatch.setattr(oss_storage, "delete_object", lambda k: None)
    return stored


@pytest.mark.asyncio
async def test_view_returns_html_with_csp(client, db, _stub_oss):
    await us.create_user(db, UserCreateIn(username="vc1", password="Passw0rd!", role="creator"))
    await db.commit()
    await client.post("/api/auth/login", json={"username": "vc1", "password": "Passw0rd!"})
    body = b"<!DOCTYPE html><html><body>HELLO</body></html>"
    up = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.html", body, "text/html")},
    )
    cid = up.json()["id"]

    r = await client.get(f"/view/{cid}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "sandbox" in r.headers["content-security-policy"]
    assert b"HELLO" in r.content


@pytest.mark.asyncio
async def test_view_requires_login(client):
    r = await client.get("/view/1")
    assert r.status_code == 401
