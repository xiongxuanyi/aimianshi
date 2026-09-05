"""题库模块业务逻辑（含 JD 生成题目，调用 LLM）。"""
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.llm.base import ChatMessage, LLMClient
from app.models.interview import QuestionTemplate
from app.modules.question.repository import TemplateRepository

GEN_SYSTEM = (
    "你是资深技术面试官。请根据岗位 JD 生成中文面试题。"
    "只输出 JSON 对象，格式为："
    '{"dimensions": ["考察维度"], "questions": [{"question": "题目", "hint": "考察要点", "dimension": "所属维度"}]}。'
    "确保是合法 JSON，不要输出任何其它内容。"
)


class QuestionService:
    def __init__(self, repo: TemplateRepository | None = None):
        self.repo = repo or TemplateRepository()

    def list_templates(self, db: Session) -> list[QuestionTemplate]:
        return self.repo.list(db)

    def get_template(self, db: Session, template_id: int) -> QuestionTemplate:
        t = self.repo.get(db, template_id)
        if t is None:
            raise NotFoundError("题库模板", str(template_id))
        return t

    def generate_questions(self, db: Session, jd: str, llm: LLMClient) -> dict:
        if not jd.strip():
            raise ValidationError("JD 不能为空")
        data = llm.chat_json(
            [
                ChatMessage(role="system", content=GEN_SYSTEM),
                ChatMessage(role="user", content=jd),
            ]
        )
        return {
            "dimensions": data.get("dimensions") or [],
            "questions": data.get("questions") or [],
        }
