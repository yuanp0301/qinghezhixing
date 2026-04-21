import pytest

from app.schemas.user import UserCreateIn
from app.services import users as svc


@pytest.mark.asyncio
async def test_login_logout_me(client, db):
    await svc.create_user(
        db,
        UserCreateIn(
            username="bob1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    await db.commit()

    r = await client.post(
        "/api/auth/login",
        json={"username": "bob1", "password": "Passw0rd!"},
    )
    assert r.status_code == 200
    assert r.cookies.get("qh_session")

    r2 = await client.get("/api/auth/me")
    assert r2.status_code == 200
    assert r2.json()["username"] == "bob1"

    r3 = await client.post("/api/auth/logout")
    assert r3.status_code == 204

    r4 = await client.get("/api/auth/me")
    assert r4.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_password(client, db):
    await svc.create_user(
        db,
        UserCreateIn(
            username="carol1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    await db.commit()
    r = await client.post(
        "/api/auth/login",
        json={"username": "carol1", "password": "nope12345"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_disabled(client, db):
    u = await svc.create_user(
        db,
        UserCreateIn(
            username="dan1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    u.status = "disabled"
    await db.commit()
    r = await client.post(
        "/api/auth/login",
        json={"username": "dan1", "password": "Passw0rd!"},
    )
    assert r.status_code == 403
