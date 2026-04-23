import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.view_log import ViewLog
from app.oss import storage
from app.services import contents as cs

router = APIRouter(tags=["view"])

_HEADERS = {
    "Content-Security-Policy": "sandbox allow-scripts allow-downloads;",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "private, no-store",
}


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/view/{content_id}")
async def view_content(
    content_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = await cs.get_active(db, content_id)
    if not c:
        raise HTTPException(404, "content not found")

    db.add(ViewLog(
        content_id=c.id,
        user_id=user.id,
        client_ip=_client_ip(request),
        user_agent=request.headers.get("user-agent", "")[:255],
    ))
    await db.commit()

    def _collect() -> list[bytes]:
        return list(storage.stream_object(c.oss_object_key))

    chunks = await asyncio.to_thread(_collect)

    async def _aiter():
        for chunk in chunks:
            yield chunk

    return StreamingResponse(_aiter(), media_type="text/html; charset=utf-8", headers=_HEADERS)
