"""评审模块数据访问层。"""
from sqlalchemy.orm import Session

from app.models.evaluation import Review


class ReviewRepository:
    def create(self, db: Session, session_id: int, reviewer_id: int, decision: str, note: str) -> Review:
        r = Review(session_id=session_id, reviewer_id=reviewer_id, decision=decision, note=note)
        db.add(r)
        db.flush()
        return r

    def list_by_session(self, db: Session, session_id: int) -> list[Review]:
        return db.query(Review).filter(Review.session_id == session_id).all()
