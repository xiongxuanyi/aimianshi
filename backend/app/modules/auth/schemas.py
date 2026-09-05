"""认证模块 Pydantic 模型。"""
from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    user_type: str

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    token: str
    user_type: str
    user: UserOut
