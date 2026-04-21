import pytest

from app.services import rate_limit as rl


@pytest.mark.asyncio
async def test_under_limit():
    k = "test:a"
    await rl.reset(k)
    for _ in range(3):
        assert await rl.check_and_bump(k, max_per_min=5) is True


@pytest.mark.asyncio
async def test_over_limit():
    k = "test:b"
    await rl.reset(k)
    for _ in range(2):
        assert await rl.check_and_bump(k, max_per_min=2) is True
    assert await rl.check_and_bump(k, max_per_min=2) is False
