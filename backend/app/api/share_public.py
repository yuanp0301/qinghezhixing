from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_db
from app.oss import storage
from app.services import share_access as sa
from app.services import shares as ss
from app.services.rate_limit import check_and_bump
from app.web.share_pages import (
    render_invalid_page,
    render_rate_limited_page,
    render_valid_page,
)

settings = get_settings()
router = APIRouter(tags=["share-public"])


_VIEW_HEADERS = {
    "Content-Security-Policy": "sandbox; default-src 'self' data:;",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "private, no-store",
}


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _invalid(resp_code: int = 404) -> Response:
    return HTMLResponse(
        render_invalid_page(), status_code=resp_code
    )


async def _rate_limited(ip: str | None) -> bool:
    if not ip:
        return False
    allowed = await check_and_bump(
        f"share-ip:{ip}",
        max_per_min=settings.share_rate_limit_per_min,
    )
    return not allowed


@router.get("/s/{token}")
async def share_entry(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    ip = _client_ip(request)
    if await _rate_limited(ip):
        return HTMLResponse(render_rate_limited_page(), status_code=429)

    res = await ss.validate_token(db, token)
    ua = request.headers.get("user-agent")
    if res.state != "valid":
        await sa.write_access_log(
            db,
            token=token,
            content_id=res.share.content_id if res.share else None,
            client_ip=ip,
            user_agent=ua,
            result=res.state,
        )
        await db.commit()
        return _invalid()

    await sa.write_access_log(
        db, token=token, content_id=res.share.content_id,
        client_ip=ip, user_agent=ua, result="success",
    )
    await db.commit()
    return HTMLResponse(
        render_valid_page(
            token=token,
            expires_at=res.share.expires_at,
            allow_download=res.share.allow_download,
        )
    )


async def _resolve_and_stream(
    token: str,
    request: Request,
    db: AsyncSession,
    *,
    disposition: str | None,
) -> Response:
    ip = _client_ip(request)
    if await _rate_limited(ip):
        return HTMLResponse(render_rate_limited_page(), status_code=429)
    res = await ss.validate_token(db, token)
    ua = request.headers.get("user-agent")
    if res.state != "valid":
        await sa.write_access_log(
            db, token=token,
            content_id=res.share.content_id if res.share else None,
            client_ip=ip, user_agent=ua, result=res.state,
        )
        await db.commit()
        return _invalid()
    # resolve content
    from app.services import contents as cs
    c = await cs.get_active(db, res.share.content_id)
    if not c:
        await sa.write_access_log(
            db, token=token, content_id=res.share.content_id,
            client_ip=ip, user_agent=ua, result="not_found",
        )
        await db.commit()
        return _invalid()

    headers = dict(_VIEW_HEADERS)
    if disposition:
        headers["Content-Disposition"] = disposition

    def _gen():
        yield from storage.stream_object(c.oss_object_key)

    chunks: list[bytes] = []
    for chunk in _gen():
        chunks.append(chunk)

    async def _aiter():
        for b in chunks:
            yield b

    return StreamingResponse(
        _aiter(),
        media_type="text/html; charset=utf-8",
        headers=headers,
    )


@router.get("/view-share/{token}")
async def view_share(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    return await _resolve_and_stream(
        token, request, db, disposition=None
    )


@router.get("/d/{token}")
async def download_share(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    # Separate validation because we also enforce allow_download.
    ip = _client_ip(request)
    if await _rate_limited(ip):
        return HTMLResponse(render_rate_limited_page(), status_code=429)
    res = await ss.validate_token(db, token)
    ua = request.headers.get("user-agent")
    if res.state != "valid" or not res.share.allow_download:
        await sa.write_access_log(
            db, token=token,
            content_id=res.share.content_id if res.share else None,
            client_ip=ip, user_agent=ua,
            result=res.state if res.state != "valid" else "not_found",
        )
        await db.commit()
        return _invalid()

    from app.services import contents as cs
    c = await cs.get_active(db, res.share.content_id)
    if not c:
        await sa.write_access_log(
            db, token=token, content_id=res.share.content_id,
            client_ip=ip, user_agent=ua, result="not_found",
        )
        await db.commit()
        return _invalid()

    filename = c.original_filename
    disposition = f'attachment; filename="{filename}"'
    return await _resolve_and_stream(
        token, request, db, disposition=disposition
    )
