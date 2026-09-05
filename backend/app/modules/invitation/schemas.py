"""邀请模块 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel


class InvitationOut(BaseModel):
    token: str
    url: str
    interview_id: int
    expires_at: datetime


class InvitationValidateOut(BaseModel):
    interview_id: int
    valid: bool
