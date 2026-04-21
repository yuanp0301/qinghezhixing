import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    calls: list[str] = []

    def fake_put(key, data, ct):
        calls.append(key)
        return {"etag": "x", "request_id": "r"}

    def fake_del(key):
        calls.append(f"del:{key}")

    monkeypatch.setattr(oss_storage, "put_object", fake_put)
    monkeypatch.setattr(oss_storage, "delete_object", fake_del)
    return calls


@pytest.mark.asyncio
async def test_upload_creates_content(client, db, _stub_oss):
    await us.create_user(db, UserCreateIn(username="up1", password="Passw0rd!", role="creator"))
    await db.commit()
    await client.post("/api/auth/login", json={"username": "up1", "password": "Passw0rd!"})

    body = b"<!DOCTYPE html><html><body>hi</body></html>"
    r = await client.post(
        "/api/contents",
        data={"title": "T", "tags": ["a", "b"]},
        files={"file": ("a.html", body, "text/html")},
    )
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["title"] == "T"
    assert {t["name"] for t in j["tags"]} == {"a", "b"}
    assert _stub_oss and _stub_oss[0].startswith("contents/")


@pytest.mark.asyncio
async def test_upload_rejects_non_html(client, db):
    await us.create_user(db, UserCreateIn(username="up2", password="Passw0rd!", role="creator"))
    await db.commit()
    await client.post("/api/auth/login", json={"username": "up2", "password": "Passw0rd!"})
    r = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.pdf", b"%PDF-...", "application/pdf")},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_viewer_cannot_upload(client, db):
    await us.create_user(db, UserCreateIn(username="viewer1", password="Passw0rd!", role="viewer"))
    await db.commit()
    await client.post("/api/auth/login", json={"username": "viewer1", "password": "Passw0rd!"})
    r = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.html", b"<html></html>", "text/html")},
    )
    assert r.status_code == 403
