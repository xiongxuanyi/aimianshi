"""面试配置模块 Pydantic 模型。"""
from pydantic import BaseModel, Field


class InterviewIn(BaseModel):
    org_id: int
    title: str = Field(min_length=1)
    position: str = Field(min_length=1)
    jd: str = ""
    question_source: str  # template | jd_generated
    questions: list
    dimension_weights: dict
    pass_thresholds: dict


class InterviewOut(BaseModel):
    id: int
    org_id: int
    title: str
    position: str
    jd: str | None
    question_source: str
    questions: list
    dimension_weights: dict
    pass_thresholds: dict
    status: str
    created_by: int

    model_config = {"from_attributes": True}


class InterviewStatusIn(BaseModel):
    status: str  # draft | published | closed
