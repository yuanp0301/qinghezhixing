"""Create or reset the initial admin account.

Usage:
    python -m app.cli.seed_admin <username> <password>
"""
import asyncio
import sys

from app.db import SessionLocal
from app.schemas.user import UserCreateIn
from app.services import users as svc
from app.security.passwords import hash_password


async def _main(username: str, password: str) -> None:
    async with SessionLocal() as db:
        existing = await svc.get_by_username(db, username)
        if existing:
            existing.password_hash = hash_password(password)
            existing.role = "admin"
            existing.status = "active"
            print(f"reset existing user {username} as admin")
        else:
            await svc.create_user(
                db,
                UserCreateIn(
                    username=username,
                    password=password,
                    role="admin",
                ),
            )
            print(f"created admin user {username}")
        await db.commit()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    asyncio.run(_main(sys.argv[1], sys.argv[2]))
