import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    stored: dict[str, bytes] = {}

    def fake_put(key, data, ct):
        stored[key] = data.read()
        return {"etag": "x", "request_id": "r"}

    def fake_stream(key):
        yield stored[key]

    monkeypatch.setattr(oss_storage, "put_object", fake_put)
    monkeypatch.setattr(oss_storage, "stream_object", fake_stream)
    monkeypatch.setattr(oss_storage, "delete_object", lambda k: None)
    return stored


async def _seed(client, db, username="shp1"):
    await us.create_user(
        db,
        UserCreateIn(
            username=username, password="Passw0rd!", role="creator"
        ),
    )
    await db.commit()
    await client.post(
        "/api/auth/login",
        json={"username": username, "password": "Passw0rd!"},
    )
    body = b"<!DOCTYPE html><html><body>HELLO</body></html>"
    r = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.html", body, "text/html")},
    )
    cid = r.json()["id"]
    r2 = await client.post(
        f"/api/contents/{cid}/shares",
        json={"expires_in_seconds": 3600, "allow_download": True},
    )
    return r2.json()["token"]


@pytest.mark.asyncio
async def test_valid_page_includes_iframe(client, db):
    token = await _seed(client, db, "shp1")
    r = await client.get(f"/s/{token}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert f"/view-share/{token}" in r.text


@pytest.mark.asyncio
async def test_view_share_returns_html_with_csp(client, db):
    token = await _seed(client, db, "shp2")
    # logout before hitting the public path so no session is required
    await client.post("/api/auth/logout")
    r = await client.get(f"/view-share/{token}")
    assert r.status_code == 200
    assert "sandbox" in r.headers["content-security-policy"]
    assert b"HELLO" in r.content


@pytest.mark.asyncio
async def test_invalid_token_returns_generic_page(client):
    r = await client.get("/s/totallyInvalidTokenX")
    assert r.status_code == 404
    assert "链接已失效" in r.text


@pytest.mark.asyncio
async def test_download_respects_flag(client, db, monkeypatch):
    token = await _seed(client, db, "shp3")
    await client.post("/api/auth/logout")

    r = await client.get(f"/d/{token}")
    assert r.status_code == 200
    assert b"HELLO" in r.content


@pytest.mark.asyncio
async def test_revoked_shows_invalid(client, db):
    token = await _seed(client, db, "shp4")
    # revoke via API as the same owner
    await client.delete(f"/api/shares/{token}")
    r = await client.get(f"/s/{token}")
    assert r.status_code == 404
    assert "链接已失效" in r.text
