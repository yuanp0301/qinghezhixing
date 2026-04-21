import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreateIn, UserUpdateIn
from app.security.passwords import hash_password


def _random_password(n: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    # Ensure at least 1 letter + 1 digit.
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(n))
        if any(c.isalpha() for c in pw) and any(c.isdigit() for c in pw):
            return pw


async def get_by_username(
    db: AsyncSession, username: str
) -> User | None:
    q = select(User).where(User.username == username)
    return (await db.execute(q)).scalar_one_or_none()


async def create_user(
    db: AsyncSession, data: UserCreateIn
) -> User:
    exists = await get_by_username(db, data.username)
    if exists:
        raise ValueError("username taken")
    u = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
        note=data.note,
    )
    db.add(u)
    await db.flush()
    return u


async def update_user(
    db: AsyncSession, user_id: int, data: UserUpdateIn
) -> User:
    u = await db.get(User, user_id)
    if not u:
        raise LookupError("user not found")
    if data.role is not None:
        u.role = data.role
    if data.status is not None:
        u.status = data.status
    if data.note is not None:
        u.note = data.note
    await db.flush()
    return u


async def reset_password(
    db: AsyncSession, user_id: int
) -> str:
    u = await db.get(User, user_id)
    if not u:
        raise LookupError("user not found")
    new = _random_password(12)
    u.password_hash = hash_password(new)
    await db.flush()
    return new


async def list_users(
    db: AsyncSession,
    *,
    q: str | None,
    role: str | None,
    status_: str | None,
    page: int,
    size: int,
) -> tuple[list[User], int]:
    stmt = select(User)
    count_stmt = select(func.count(User.id))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(User.username.ilike(pattern))
        count_stmt = count_stmt.where(User.username.ilike(pattern))
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    if status_:
        stmt = stmt.where(User.status == status_)
        count_stmt = count_stmt.where(User.status == status_)
    stmt = (
        stmt.order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return list(rows), total
