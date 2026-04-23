from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_db
from app.models.share_key import ShareKey
from app.models.share_usage_event import ShareUsageEvent
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
    "Content-Security-Policy": "sandbox allow-scripts allow-downloads;",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "private, no-store",
}
_PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _invalid(resp_code: int = 404) -> Response:
    return HTMLResponse(
        render_invalid_page(), status_code=resp_code
    )


def _build_tracking_script(token: str) -> str:
    report_base = settings.public_base_url.rstrip("/")
    return f"""
<script>
(function () {{
  var REPORT_BASE = "{report_base}";
  var TOKEN = "{token}";
  var QUEUE_KEY = "qh_share_open_queue_v1";

  function rid() {{
    return "evt_" + Date.now() + "_" + Math.random().toString(36).slice(2, 12);
  }}

  function loadQueue() {{
    try {{
      return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
    }} catch (_err) {{
      return [];
    }}
  }}

  function saveQueue(queue) {{
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue.slice(-500)));
  }}

  function enqueue(item) {{
    var q = loadQueue();
    q.push(item);
    saveQueue(q);
  }}

  function sendEvent(item) {{
    return new Promise(function (resolve) {{
      var img = new Image();
      img.onload = function () {{ resolve(true); }};
      img.onerror = function () {{ resolve(false); }};
      var url = REPORT_BASE + "/api/share-events/pixel.gif"
        + "?token=" + encodeURIComponent(item.token)
        + "&event_id=" + encodeURIComponent(item.event_id)
        + "&opened_at=" + encodeURIComponent(item.opened_at)
        + "&offline_replay=" + (item.offline_replay ? "1" : "0");
      img.src = url;
    }});
  }}

  async function flushQueue() {{
    if (!navigator.onLine) return;
    var q = loadQueue();
    if (!q.length) return;
    var remain = [];
    for (var i = 0; i < q.length; i++) {{
      var ok = await sendEvent(q[i]);
      if (!ok) remain.push(q[i]);
    }}
    saveQueue(remain);
  }}

  var eventItem = {{
    event_id: rid(),
    token: TOKEN,
    opened_at: new Date().toISOString(),
    offline_replay: !navigator.onLine
  }};
  enqueue(eventItem);
  flushQueue();
  window.addEventListener("online", flushQueue);
  document.addEventListener("visibilitychange", function () {{
    if (document.visibilityState === "visible") flushQueue();
  }});
}})();
</script>
""".strip()


def _inject_tracking_script(html: str, token: str) -> str:
    script = _build_tracking_script(token)
    lower = html.lower()
    idx = lower.rfind("</head>")
    if idx != -1:
        return html[:idx] + script + html[idx:]
    idx = lower.rfind("</body>")
    if idx != -1:
        return html[:idx] + script + html[idx:]
    return html + script


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
    use_mode: str,
    inject_tracking: bool,
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

    await ss.mark_key_used(db, token=token, use_mode=use_mode)
    await db.commit()

    headers = dict(_VIEW_HEADERS)
    if disposition:
        headers["Content-Disposition"] = disposition

    chunks = list(storage.stream_object(c.oss_object_key))
    if not inject_tracking:
        async def _aiter():
            for b in chunks:
                yield b

        return StreamingResponse(
            _aiter(),
            media_type="text/html; charset=utf-8",
            headers=headers,
        )

    raw = b"".join(chunks)
    html = raw.decode("utf-8", errors="replace")
    html = _inject_tracking_script(html, token)
    return HTMLResponse(
        html,
        headers=headers,
    )


@router.get("/view-share/{token}")
async def view_share(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    return await _resolve_and_stream(
        token, request, db, use_mode="preview", inject_tracking=False, disposition=None
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
    filename_enc = quote(filename)
    disposition = (
        f'attachment; filename="download.html"; '
        f"filename*=UTF-8''{filename_enc}"
    )
    return await _resolve_and_stream(
        token, request, db, use_mode="download", inject_tracking=True, disposition=disposition
    )


@router.get("/api/share-events/pixel.gif")
async def report_download_open(
    token: str,
    event_id: str,
    request: Request,
    opened_at: str | None = None,
    offline_replay: str = "0",
    db: AsyncSession = Depends(get_db),
) -> Response:
    event = event_id.strip()[:64]
    if not event:
        return Response(content=_PIXEL_GIF, media_type="image/gif")
    exists = await db.execute(
        select(ShareUsageEvent.id).where(ShareUsageEvent.event_id == event)
    )
    if exists.scalar_one_or_none():
        return Response(content=_PIXEL_GIF, media_type="image/gif")

    share = await ss.get_by_token(db, token)
    if not share:
        return Response(content=_PIXEL_GIF, media_type="image/gif")

    key_row = (
        await db.execute(select(ShareKey).where(ShareKey.key == token))
    ).scalar_one_or_none()
    opened_dt: datetime | None = None
    if opened_at:
        try:
            opened_dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
        except ValueError:
            opened_dt = None

    ip = _client_ip(request)
    ua = request.headers.get("user-agent")
    db.add(
        ShareUsageEvent(
            event_id=event,
            token=token,
            content_id=share.content_id,
            share_key_id=key_row.id if key_row else None,
            user_info=key_row.user_info if key_row else None,
            opened_at=opened_dt,
            opened_via="download",
            is_offline_replay=offline_replay == "1",
            client_ip=ip,
            user_agent=(ua or "")[:255] or None,
        )
    )
    await db.commit()
    return Response(content=_PIXEL_GIF, media_type="image/gif")
