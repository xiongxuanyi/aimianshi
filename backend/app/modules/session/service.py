"""会话模块业务逻辑（面试对话编排）。"""
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.llm.base import ChatMessage, LLMClient
from app.models.session import InterviewSession, Message
from app.modules.interview.repository import InterviewRepository
from app.modules.session.repository import MessageRepository, SessionRepository

SYSTEM_PROMPT = (
    "你是专业的 AI 面试官，正在进行一场中文面试。"
    "请根据面试题目和候选人的回答，自然地提问、追问或点评。回复简洁、使用中文。"
)

GREETING = "你好，我是本次的 AI 面试官。接下来我会围绕岗位要求向你提问，请尽量具体作答。准备好了吗？"


class SessionService:
    def __init__(
        self,
        session_repo: SessionRepository | None = None,
        message_repo: MessageRepository | None = None,
        interview_repo: InterviewRepository | None = None,
    ):
        self.session_repo = session_repo or SessionRepository()
        self.message_repo = message_repo or MessageRepository()
        self.interview_repo = interview_repo or InterviewRepository()

    def start(self, db: Session, interview_id: int, candidate_id: int) -> InterviewSession:
        if self.interview_repo.get(db, interview_id) is None:
            raise NotFoundError("面试", str(interview_id))
        existing = self.session_repo.get_by_interview_and_candidate(db, interview_id, candidate_id)
        if existing is not None:
            return existing
        session = self.session_repo.create(db, interview_id, candidate_id)
        self.message_repo.create(db, session.id, "interviewer", GREETING, "text", 1)
        db.commit()
        db.refresh(session)
        return session

    def get(self, db: Session, session_id: int, candidate_id: int) -> InterviewSession:
        session = self.session_repo.get(db, session_id)
        if session is None:
            raise NotFoundError("面试会话", str(session_id))
        if session.candidate_id != candidate_id:
            raise ForbiddenError("无权访问该会话")
        return session

    def list_messages(self, db: Session, session_id: int, candidate_id: int) -> list[Message]:
        self.get(db, session_id, candidate_id)
        return self.message_repo.list_by_session(db, session_id)

    def send_message(
        self, db: Session, session_id: int, candidate_id: int, content: str, kind: str, llm: LLMClient
    ) -> Message:
        session = self.get(db, session_id, candidate_id)
        if not content.strip():
            raise ValidationError("消息内容不能为空")
        seq = self.message_repo.next_seq(db, session_id)
        self.message_repo.create(db, session_id, "candidate", content, kind, seq)
        prompt = self._build_prompt(db, session)
        reply = llm.chat(prompt)
        reply_msg = self.message_repo.create(db, session_id, "interviewer", reply, "text", seq + 1)
        db.commit()
        db.refresh(reply_msg)
        return reply_msg

    def _build_prompt(self, db: Session, session: InterviewSession) -> list[ChatMessage]:
        interview = self.interview_repo.get(db, session.interview_id)
        msgs = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
        if interview and interview.questions:
            qtext = "\n".join(
                f"{i + 1}. {q.get('question', '')}" for i, q in enumerate(interview.questions)
            )
            msgs.append(ChatMessage(role="system", content=f"面试题目：\n{qtext}"))
        for m in self.message_repo.list_by_session(db, session.id):
            role = "assistant" if m.role == "interviewer" else "user"
            msgs.append(ChatMessage(role=role, content=m.content))
        return msgs
