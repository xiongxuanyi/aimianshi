"""面试配置模块数据访问层。"""
from sqlalchemy.orm import Session

from app.models.interview import Interview


class InterviewRepository:
    def create(self, db: Session, **fields) -> Interview:
        iv = Interview(**fields)
        db.add(iv)
        db.flush()
        return iv

    def get(self, db: Session, interview_id: int) -> Interview | None:
        return db.get(Interview, interview_id)

    def list_by_org(self, db: Session, org_id: int) -> list[Interview]:
        return db.query(Interview).filter(Interview.org_id == org_id).all()

    def list_all(self, db: Session) -> list[Interview]:
        return db.query(Interview).all()
