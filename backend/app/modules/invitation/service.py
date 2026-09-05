"""邀请模块业务逻辑。"""
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.invitation import Invitation
from app.modules.interview.repository import InterviewRepository
from app.modules.invitation.repository import InvitationRepository

INVITE_VALID_DAYS = 7


class InvitationService:
    def __init__(
        self,
        repo: InvitationRepository | None = None,
        interview_repo: InterviewRepository | None = None,
    ):
        self.repo = repo or InvitationRepository()
        self.interview_repo = interview_repo or InterviewRepository()

    def create(self, db: Session, interview_id: int, creator_id: int) -> dict:
        if self.interview_repo.get(db, interview_id) is None:
            raise NotFoundError("面试", str(interview_id))
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=INVITE_VALID_DAYS)
        inv = self.repo.create(db, interview_id, token, expires_at, creator_id)
        db.commit()
        db.refresh(inv)
        return {
            "token": inv.token,
            "url": f"/candidate/invite/{inv.token}",
            "interview_id": inv.interview_id,
            "expires_at": inv.expires_at,
        }

    def validate(self, db: Session, token: str) -> Invitation:
        inv = self.repo.get_by_token(db, token)
        if inv is None:
            raise NotFoundError("邀请", token)
        if inv.expires_at < datetime.utcnow():
            raise ValidationError("邀请已过期")
        return inv
