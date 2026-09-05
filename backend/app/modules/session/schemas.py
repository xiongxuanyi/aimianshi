"""会话模块 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel


class SessionCreateIn(BaseModel):
    interview_id: int


class SessionOut(BaseModel):
    id: int
    interview_id: int
    candidate_id: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    kind: str
    seq: int

    model_config = {"from_attributes": True}


class SendMessageIn(BaseModel):
    content: str
    kind: str = "text"
