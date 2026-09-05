"""题库模块数据访问层。"""
from sqlalchemy.orm import Session

from app.models.interview import QuestionTemplate


class TemplateRepository:
    def list(self, db: Session) -> list[QuestionTemplate]:
        return db.query(QuestionTemplate).all()

    def get(self, db: Session, template_id: int) -> QuestionTemplate | None:
        return db.get(QuestionTemplate, template_id)
