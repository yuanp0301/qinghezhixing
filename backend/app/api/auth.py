from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import LoginIn, LoginOut, UserOut
from app.security.passwords import verify_password
from app.security.sessions import create_session, delete_session
from app.services.audit import write_audit
from app.services.users import get_by_username

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(resp: Response, sid: str) -> None:
    resp.set_cookie(
        settings.session_cookie_name,
        sid,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite=settings.session_cookie_samesite,
        secure=settings.session_cookie_use_secure(),
        path="/",
    )


@router.post("/login", response_model=LoginOut)
async def login(
    data: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginOut:
    user = await get_by_username(db, data.username)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid credentials"
        )
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")

    sid = await create_session(db, user.id, settings.session_ttl_seconds)
    _set_cookie(response, sid)
    user.last_login_at = datetime.utcnow()
    await write_audit(
        db, actor_id=user.id, action="login",
        target_type="user", target_id=user.id,
    )
    await db.commit()
    return LoginOut(user=UserOut.model_validate(user))


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    qh_session: str | None = Cookie(default=None, alias="qh_session"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if qh_session:
        await delete_session(db, qh_session)
        await db.commit()
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_use_secure(),
        samesite=settings.session_cookie_samesite,
    )
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
