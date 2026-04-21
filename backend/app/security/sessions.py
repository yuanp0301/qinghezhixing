import json
import secrets

from app.redis_conn import redis

_PREFIX = "sess:"


async def create_session(user_id: int, ttl_seconds: int) -> str:
    sid = secrets.token_urlsafe(32)
    await redis.set(
        _PREFIX + sid,
        json.dumps({"user_id": user_id}),
        ex=ttl_seconds,
    )
    return sid


async def get_session(sid: str) -> dict | None:
    raw = await redis.get(_PREFIX + sid)
    return json.loads(raw) if raw else None


async def delete_session(sid: str) -> None:
    await redis.delete(_PREFIX + sid)


async def touch_session(sid: str, ttl_seconds: int) -> None:
    await redis.expire(_PREFIX + sid, ttl_seconds)
