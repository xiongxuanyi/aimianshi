"""评分模块 Pydantic 模型。"""
from pydantic import BaseModel


class EvaluationOut(BaseModel):
    id: int
    session_id: int
    total_score: int
    dimension_scores: dict
    per_question: list
    highlights: str
    weaknesses: str
    recommendation: str
    reason: str

    model_config = {"from_attributes": True}
