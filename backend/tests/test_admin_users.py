import pytest

from app.schemas.user import UserCreateIn
from app.services import users as svc


async def _login(client, db, username, role="admin"):
    await svc.create_user(
        db,
        UserCreateIn(
            username=username,
            password="Passw0rd!",
            role=role,
        ),
    )
    await db.commit()
    r = await client.post(
        "/api/auth/login",
        json={"username": username, "password": "Passw0rd!"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_create_and_list(client, db):
    await _login(client, db, "admin1", "admin")

    r = await client.post(
        "/api/admin/users",
        json={
            "username": "newone1",
            "password": "Initial12",
            "role": "creator",
        },
    )
    assert r.status_code == 201
    assert r.json()["username"] == "newone1"

    r2 = await client.get("/api/admin/users?page=1&size=20")
    assert r2.status_code == 200
    assert r2.json()["total"] >= 2


@pytest.mark.asyncio
async def test_non_admin_forbidden(client, db):
    await _login(client, db, "creator1", "creator")
    r = await client.get("/api/admin/users")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_reset_password(client, db):
    await _login(client, db, "admin2", "admin")
    r = await client.post(
        "/api/admin/users",
        json={
            "username": "resetme1",
            "password": "Initial12",
            "role": "viewer",
        },
    )
    uid = r.json()["id"]
    r2 = await client.post(f"/api/admin/users/{uid}/reset-password")
    assert r2.status_code == 200
    assert len(r2.json()["new_password"]) == 12
