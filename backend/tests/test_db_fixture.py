import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_db_connects(db):
    r = await db.execute(text("select 1"))
    assert r.scalar() == 1
