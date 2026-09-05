"""题库模块路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_llm, require_enterprise
from app.llm.base import LLMClient
from app.models.user import User
from app.modules.question.schemas import GeneratedQuestionsOut, JdIn, TemplateOut
from app.modules.question.service import QuestionService

router = APIRouter(tags=["question"])
service = QuestionService()


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), me: User = Depends(require_enterprise)):
    return service.list_templates(db)


@router.get("/templates/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db), me: User = Depends(require_enterprise)):
    return service.get_template(db, template_id)


@router.post("/interviews/generate-questions", response_model=GeneratedQuestionsOut)
def generate_questions(
    body: JdIn,
    db: Session = Depends(get_db),
    me: User = Depends(require_enterprise),
    llm: LLMClient = Depends(get_llm),
):
    return service.generate_questions(db, body.jd, llm)
