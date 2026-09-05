"""评分模块业务逻辑（LLM 结构化评分）。"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.llm.base import ChatMessage, LLMClient
from app.models.evaluation import Evaluation
from app.modules.evaluation.repository import EvaluationRepository
from app.modules.session.repository import MessageRepository, SessionRepository

EVAL_SYSTEM = (
    "你是资深面试评估官。根据面试对话记录对候选人进行结构化评分。"
    "只输出 JSON 对象，格式为："
    '{"total_score": 0到100的整数, "dimension_scores": {"维度名": 0到100的整数}, '
    '"per_question": [{"question": "题目", "comment": "点评"}], '
    '"highlights": "亮点", "weaknesses": "不足", '
    '"recommendation": "pass/pending/reject", "reason": "推荐理由"}。'
    "确保是合法 JSON，不要输出任何其它内容。"
)

REQUIRED_FIELDS = [
    "total_score",
    "dimension_scores",
    "per_question",
    "highlights",
    "weaknesses",
    "recommendation",
    "reason",
]


class EvaluationService:
    def __init__(
        self,
        eval_repo: EvaluationRepository | None = None,
        session_repo: SessionRepository | None = None,
        message_repo: MessageRepository | None = None,
    ):
        self.eval_repo = eval_repo or EvaluationRepository()
        self.session_repo = session_repo or SessionRepository()
        self.message_repo = message_repo or MessageRepository()

    def evaluate(self, db: Session, session_id: int, llm: LLMClient) -> Evaluation:
        session = self.session_repo.get(db, session_id)
        if session is None:
            raise NotFoundError("面试会话", str(session_id))
        messages = self.message_repo.list_by_session(db, session_id)
        transcript = "\n".join(
            f"{'面试官' if m.role == 'interviewer' else '候选人'}：{m.content}" for m in messages
        )
        data = llm.chat_json(
            [
                ChatMessage(role="system", content=EVAL_SYSTEM),
                ChatMessage(role="user", content=transcript),
            ]
        )
        for field in REQUIRED_FIELDS:
            if field not in data:
                raise ValidationError(f"评分结果缺少字段：{field}")
        ev = self.eval_repo.create(
            db,
            session_id=session_id,
            total_score=data["total_score"],
            dimension_scores=data["dimension_scores"],
            per_question=data["per_question"],
            highlights=data["highlights"],
            weaknesses=data["weaknesses"],
            recommendation=data["recommendation"],
            reason=data["reason"],
        )
        session.status = "evaluated"
        session.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(ev)
        return ev

    def get_evaluation(self, db: Session, session_id: int) -> Evaluation:
        ev = self.eval_repo.get_by_session(db, session_id)
        if ev is None:
            raise NotFoundError("评估报告", str(session_id))
        return ev
