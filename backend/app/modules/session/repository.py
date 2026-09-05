"""会话模块数据访问层。"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.session import InterviewSession, Message


class SessionRepository:
    def create(self, db: Session, interview_id: int, candidate_id: int) -> InterviewSession:
        s = InterviewSession(interview_id=interview_id, candidate_id=candidate_id, status="in_progress")
        db.add(s)
        db.flush()
        return s

    def get(self, db: Session, session_id: int) -> InterviewSession | None:
        return db.get(InterviewSession, session_id)

    def get_by_interview_and_candidate(
        self, db: Session, interview_id: int, candidate_id: int
    ) -> InterviewSession | None:
        return (
            db.query(InterviewSession)
            .filter(
                InterviewSession.interview_id == interview_id,
                InterviewSession.candidate_id == candidate_id,
            )
            .first()
        )


class MessageRepository:
    def create(self, db: Session, session_id: int, role: str, content: str, kind: str, seq: int) -> Message:
        m = Message(session_id=session_id, role=role, content=content, kind=kind, seq=seq)
        db.add(m)
        db.flush()
        return m

    def list_by_session(self, db: Session, session_id: int) -> list[Message]:
        return (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.seq)
            .all()
        )

    def next_seq(self, db: Session, session_id: int) -> int:
        max_seq = db.query(func.max(Message.seq)).filter(Message.session_id == session_id).scalar()
        return (max_seq or 0) + 1
