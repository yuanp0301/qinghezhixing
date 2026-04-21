from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=8, max_length=64)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    status: str

    class Config:
        from_attributes = True


class LoginOut(BaseModel):
    user: UserOut
