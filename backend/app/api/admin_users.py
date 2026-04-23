from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import (
    PasswordResetOut,
    UserAdminOut,
    UserCreateIn,
    UserUpdateIn,
)
from app.services import users as svc
from app.services.audit import write_audit

router = APIRouter(
    prefix="/api/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_role("admin"))],
)


def _out(u: User) -> UserAdminOut:
    return UserAdminOut(
        id=u.id,
        username=u.username,
        role=u.role,
        status=u.status,
        note=u.note,
        last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        created_at=u.created_at.isoformat(),
    )


@router.get("", response_model=Page[UserAdminOut])
async def list_users(
    q: str | None = None,
    role: str | None = None,
    status_: str | None = Query(default=None, alias="status"),
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
) -> Page[UserAdminOut]:
    rows, total = await svc.list_users(
        db, q=q, role=role, status_=status_, page=page, size=size
    )
    return Page[UserAdminOut](
        items=[_out(r) for r in rows],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=UserAdminOut, status_code=201)
async def create_user(
    data: UserCreateIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> UserAdminOut:
    try:
        u = await svc.create_user(db, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    await write_audit(
        db, actor_id=actor.id, action="user.create",
        target_type="user", target_id=u.id,
        detail={"username": u.username, "role": u.role},
    )
    await db.commit()
    return _out(u)


@router.patch("/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: int,
    data: UserUpdateIn,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> UserAdminOut:
    try:
        u = await svc.update_user(db, user_id, data)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    await write_audit(
        db, actor_id=actor.id, action="user.update",
        target_type="user", target_id=u.id,
        detail=data.model_dump(exclude_none=True),
    )
    await db.commit()
    return _out(u)


@router.post(
    "/{user_id}/reset-password", response_model=PasswordResetOut
)
async def reset_password(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role("admin")),
) -> PasswordResetOut:
    try:
        new = await svc.reset_password(db, user_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    await write_audit(
        db, actor_id=actor.id, action="user.reset_password",
        target_type="user", target_id=user_id,
    )
    await db.commit()
    return PasswordResetOut(new_password=new)
