"""会话模块路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_llm, require_candidate
from app.llm.base import LLMClient
from app.models.user import User
from app.modules.session.schemas import MessageOut, SendMessageIn, SessionCreateIn, SessionOut
from app.modules.session.service import SessionService

router = APIRouter(prefix="/sessions", tags=["session"])
service = SessionService()


@router.post("", response_model=SessionOut)
def start_session(body: SessionCreateIn, db: Session = Depends(get_db), me: User = Depends(require_candidate)):
    return service.start(db, body.interview_id, me.id)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db), me: User = Depends(require_candidate)):
    return service.get(db, session_id, me.id)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: int, db: Session = Depends(get_db), me: User = Depends(require_candidate)):
    return service.list_messages(db, session_id, me.id)


@router.post("/{session_id}/messages", response_model=MessageOut)
def send_message(
    session_id: int,
    body: SendMessageIn,
    db: Session = Depends(get_db),
    me: User = Depends(require_candidate),
    llm: LLMClient = Depends(get_llm),
):
    return service.send_message(db, session_id, me.id, body.content, body.kind, llm)
