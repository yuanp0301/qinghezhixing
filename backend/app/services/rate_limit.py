from app.redis_conn import redis

_PREFIX = "rl:"


async def check_and_bump(key: str, *, max_per_min: int) -> bool:
    """Return True if request is allowed, False if over limit."""
    full = _PREFIX + key
    n = await redis.incr(full)
    if n == 1:
        await redis.expire(full, 60)
    return n <= max_per_min


async def reset(key: str) -> None:
    await redis.delete(_PREFIX + key)
