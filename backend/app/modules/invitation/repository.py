"""邀请模块数据访问层。"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.invitation import Invitation


class InvitationRepository:
    def create(
        self,
        db: Session,
        interview_id: int,
        token: str,
        expires_at: datetime,
        created_by: int | None,
    ) -> Invitation:
        inv = Invitation(
            interview_id=interview_id, token=token, expires_at=expires_at, created_by=created_by
        )
        db.add(inv)
        db.flush()
        return inv

    def get_by_token(self, db: Session, token: str) -> Invitation | None:
        return db.query(Invitation).filter(Invitation.token == token).first()
