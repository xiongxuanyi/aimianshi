"""评审模块业务逻辑。"""
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.evaluation import Review
from app.modules.review.repository import ReviewRepository
from app.modules.session.repository import SessionRepository

VALID_DECISION = {"pass", "reject", "pending"}


class ReviewService:
    def __init__(
        self,
        repo: ReviewRepository | None = None,
        session_repo: SessionRepository | None = None,
    ):
        self.repo = repo or ReviewRepository()
        self.session_repo = session_repo or SessionRepository()

    def add_review(self, db: Session, session_id: int, reviewer_id: int, decision: str, note: str) -> Review:
        if self.session_repo.get(db, session_id) is None:
            raise NotFoundError("面试会话", str(session_id))
        if decision not in VALID_DECISION:
            raise ValidationError("决策只能是 pass/reject/pending")
        r = self.repo.create(db, session_id, reviewer_id, decision, note)
        db.commit()
        db.refresh(r)
        return r

    def list_reviews(self, db: Session, session_id: int) -> list[Review]:
        return self.repo.list_by_session(db, session_id)
