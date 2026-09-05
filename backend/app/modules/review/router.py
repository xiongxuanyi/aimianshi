"""评审模块路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_enterprise
from app.models.user import User
from app.modules.review.schemas import ReviewIn, ReviewOut
from app.modules.review.service import ReviewService

router = APIRouter(tags=["review"])
service = ReviewService()


@router.post("/sessions/{session_id}/review", response_model=ReviewOut)
def add_review(
    session_id: int,
    body: ReviewIn,
    db: Session = Depends(get_db),
    me: User = Depends(require_enterprise),
):
    return service.add_review(db, session_id, me.id, body.decision, body.note)


@router.get("/sessions/{session_id}/reviews", response_model=list[ReviewOut])
def list_reviews(session_id: int, db: Session = Depends(get_db), me: User = Depends(require_enterprise)):
    return service.list_reviews(db, session_id)
