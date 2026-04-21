import pytest

from app.oss import storage as oss_storage
from app.schemas.user import UserCreateIn
from app.services import users as us


@pytest.fixture(autouse=True)
def _stub_oss(monkeypatch):
    monkeypatch.setattr(oss_storage, "put_object", lambda k, d, ct: {"etag": "x", "request_id": "r"})


async def _login(client, db, name, role):
    await us.create_user(db, UserCreateIn(username=name, password="Passw0rd!", role=role))
    await db.commit()
    await client.post("/api/auth/login", json={"username": name, "password": "Passw0rd!"})


@pytest.mark.asyncio
async def test_admin_all_includes_deleted_and_restore(client, db):
    await _login(client, db, "admA", "admin")
    body = b"<!DOCTYPE html><html><body>x</body></html>"
    up = await client.post(
        "/api/contents",
        data={"title": "T"},
        files={"file": ("a.html", body, "text/html")},
    )
    cid = up.json()["id"]
    await client.delete(f"/api/contents/{cid}")

    r = await client.get("/api/contents/admin/all?status=deleted")
    assert any(it["id"] == cid for it in r.json()["items"])

    rs = await client.post(f"/api/contents/{cid}/restore")
    assert rs.json()["status"] == "active"
