import re

from pydantic import BaseModel, Field, field_validator

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{2,32}$")


class UserCreateIn(BaseModel):
    username: str
    password: str = Field(min_length=8, max_length=64)
    role: str = Field(pattern=r"^(admin|creator|viewer)$")
    note: str | None = Field(default=None, max_length=200)

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError(
                "username must be 2-32 chars of [A-Za-z0-9_]"
            )
        return v

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if not (
            any(c.isalpha() for c in v) and any(c.isdigit() for c in v)
        ):
            raise ValueError(
                "password must contain letters and digits"
            )
        return v


class UserUpdateIn(BaseModel):
    role: str | None = Field(default=None, pattern=r"^(admin|creator|viewer)$")
    status: str | None = Field(default=None, pattern=r"^(active|disabled)$")
    note: str | None = Field(default=None, max_length=200)


class UserAdminOut(BaseModel):
    id: int
    username: str
    role: str
    status: str
    note: str | None
    last_login_at: str | None = None
    created_at: str

    class Config:
        from_attributes = True


class PasswordResetOut(BaseModel):
    new_password: str
