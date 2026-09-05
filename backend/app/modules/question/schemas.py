"""题库模块 Pydantic 模型。"""
from pydantic import BaseModel, Field


class TemplateOut(BaseModel):
    id: int
    title: str
    industry: str
    position: str
    dimensions: list
    questions: list

    model_config = {"from_attributes": True}


class JdIn(BaseModel):
    jd: str


class GeneratedQuestionsOut(BaseModel):
    dimensions: list
    questions: list
