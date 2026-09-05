"""面试配置模块路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_enterprise
from app.models.user import User
from app.modules.interview.schemas import InterviewIn, InterviewOut, InterviewStatusIn
from app.modules.interview.service import InterviewService

router = APIRouter(prefix="/interviews", tags=["interview"])
service = InterviewService()


@router.post("", response_model=InterviewOut)
def create(body: InterviewIn, db: Session = Depends(get_db), me: User = Depends(require_enterprise)):
    return service.create(db, body.model_dump(), me.id)


@router.get("", response_model=list[InterviewOut])
def list_interviews(
    org_id: int | None = Query(None),
    db: Session = Depends(get_db),
    me: User = Depends(require_enterprise),
):
    return service.list_interviews(db, org_id)


@router.get("/{interview_id}", response_model=InterviewOut)
def get_interview(interview_id: int, db: Session = Depends(get_db), me: User = Depends(require_enterprise)):
    return service.get(db, interview_id)


@router.patch("/{interview_id}/status", response_model=InterviewOut)
def update_status(
    interview_id: int,
    body: InterviewStatusIn,
    db: Session = Depends(get_db),
    me: User = Depends(require_enterprise),
):
    return service.update_status(db, interview_id, body.status)
