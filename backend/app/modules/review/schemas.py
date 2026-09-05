"""评审模块 Pydantic 模型。"""
from pydantic import BaseModel


class ReviewIn(BaseModel):
    decision: str  # pass | reject | pending
    note: str = ""


class ReviewOut(BaseModel):
    id: int
    session_id: int
    reviewer_id: int
    decision: str
    note: str | None

    model_config = {"from_attributes": True}
