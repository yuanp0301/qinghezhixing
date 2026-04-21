import pytest

from app.schemas.user import UserCreateIn, UserUpdateIn
from app.services import users as svc


@pytest.mark.asyncio
async def test_create_update_reset(db):
    u = await svc.create_user(
        db,
        UserCreateIn(
            username="alice1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    assert u.id and u.status == "active"

    u2 = await svc.update_user(
        db, u.id, UserUpdateIn(role="creator", status="disabled")
    )
    assert u2.role == "creator" and u2.status == "disabled"

    new_pw = await svc.reset_password(db, u.id)
    assert len(new_pw) == 12
    assert any(c.isalpha() for c in new_pw)
    assert any(c.isdigit() for c in new_pw)


@pytest.mark.asyncio
async def test_duplicate_username(db):
    await svc.create_user(
        db,
        UserCreateIn(
            username="dupe1",
            password="Passw0rd!",
            role="viewer",
        ),
    )
    with pytest.raises(ValueError):
        await svc.create_user(
            db,
            UserCreateIn(
                username="dupe1",
                password="Passw0rd!",
                role="viewer",
            ),
        )
