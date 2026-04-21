import pytest

from app.schemas.user import UserCreateIn
from app.services import users as us


async def _admin(client, db, name="adm_tag1"):
    await us.create_user(db, UserCreateIn(username=name, password="Passw0rd!", role="admin"))
    await db.commit()
    await client.post("/api/auth/login", json={"username": name, "password": "Passw0rd!"})


@pytest.mark.asyncio
async def test_create_rename_delete_merge(client, db):
    await _admin(client, db)
    r = await client.post("/api/admin/tags", json={"name": "alpha"})
    a_id = r.json()["id"]
    r2 = await client.post("/api/admin/tags", json={"name": "beta"})
    b_id = r2.json()["id"]

    rn = await client.patch(f"/api/admin/tags/{a_id}", json={"name": "alpha2"})
    assert rn.json()["name"] == "alpha2"

    mg = await client.post(f"/api/admin/tags/{a_id}/merge", json={"target_id": b_id})
    assert mg.status_code == 200

    lst = await client.get("/api/admin/tags")
    names = [t["name"] for t in lst.json()]
    assert "alpha2" not in names
