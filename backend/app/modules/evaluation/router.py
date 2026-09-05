"""评分模块路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_llm, require_enterprise
from app.llm.base import LLMClient
from app.models.user import User
from app.modules.evaluation.schemas import EvaluationOut
from app.modules.evaluation.service import EvaluationService

router = APIRouter(tags=["evaluation"])
service = EvaluationService()


@router.post("/sessions/{session_id}/evaluate", response_model=EvaluationOut)
def evaluate(
    session_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(require_enterprise),
    llm: LLMClient = Depends(get_llm),
):
    return service.evaluate(db, session_id, llm)


@router.get("/sessions/{session_id}/evaluation", response_model=EvaluationOut)
def get_evaluation(
    session_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(require_enterprise),
):
    return service.get_evaluation(db, session_id)
