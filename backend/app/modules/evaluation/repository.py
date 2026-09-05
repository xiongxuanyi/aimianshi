"""评分模块数据访问层。"""
from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation


class EvaluationRepository:
    def create(self, db: Session, **fields) -> Evaluation:
        ev = Evaluation(**fields)
        db.add(ev)
        db.flush()
        return ev

    def get_by_session(self, db: Session, session_id: int) -> Evaluation | None:
        return db.query(Evaluation).filter(Evaluation.session_id == session_id).first()
