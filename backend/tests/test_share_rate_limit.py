import pytest

from app.api import share_public
from app.services import rate_limit as rl


@pytest.mark.asyncio
async def test_share_endpoint_rate_limits(client, monkeypatch):
    monkeypatch.setattr(
        share_public.settings, "share_rate_limit_per_min", 2
    )
    await rl.reset("share-ip:127.0.0.1")

    for _ in range(2):
        r = await client.get("/s/doesnotmatter")
        assert r.status_code == 404

    r3 = await client.get("/s/doesnotmatter")
    assert r3.status_code == 429
    assert "访问过于频繁" in r3.text