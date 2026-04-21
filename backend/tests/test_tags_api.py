import pytest

from app.schemas.user import UserCreateIn
from app.services import tags as ts
from app.services import users as us


@pytest.mark.asyncio
async def test_list_tags(client, db):
    await us.create_user(db, UserCreateIn(username="tg1", password="Passw0rd!", role="viewer"))
    await ts.get_or_create_many(db, ["α", "β", "γ"])
    await db.commit()
    await client.post("/api/auth/login", json={"username": "tg1", "password": "Passw0rd!"})

    r = await client.get("/api/tags?q=α")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "α" in names
