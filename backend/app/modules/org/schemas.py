"""组织模块 Pydantic 模型。"""
from pydantic import BaseModel, Field


class OrgIn(BaseModel):
    name: str = Field(min_length=1)


class OrgOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class MemberIn(BaseModel):
    email: str
    role: str  # admin | hr


class MemberOut(BaseModel):
    id: int
    org_id: int
    user_id: int
    role: str
    user_name: str
    user_email: str
