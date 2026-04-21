from sqlalchemy.ext.asyncio import AsyncSession

from app.models.share_access_log import ShareAccessLog


def _mask_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return ip.split(":")[0] + "::*"


async def write_access_log(
    db: AsyncSession,
    *,
    token: str,
    content_id: int | None,
    client_ip: str | None,
    user_agent: str | None,
    result: str,
) -> None:
    db.add(
        ShareAccessLog(
            token=token,
            content_id=content_id,
            client_ip=client_ip,
            user_agent=(user_agent or "")[:255] or None,
            result=result,
        )
    )


def mask_ip(ip: str | None) -> str | None:
    return _mask_ip(ip)
