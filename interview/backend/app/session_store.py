"""线程安全的内存会话存储 + TTL 惰性清理。"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, List, Optional

from .config import settings
from .schemas import InterviewQuestion


class InterviewSession:
    def __init__(
        self,
        *,
        resume: dict,
        jd: dict,
        questions: List[InterviewQuestion],
    ):
        self.session_id: str = uuid.uuid4().hex
        self.resume: dict = resume or {}
        self.jd: dict = jd or {}
        self.questions: List[InterviewQuestion] = list(questions)
        self.current_idx: int = 0
        self.current_q: Optional[InterviewQuestion] = self.questions[0] if self.questions else None
        self.round: int = 0
        self.followup_count: int = 0
        self.history: List[dict] = []
        self.started_at: float = time.time()
        self.last_active_at: float = time.time()
        self.finished: bool = False
        self.evaluation: Optional[dict] = None

    def touch(self):
        self.last_active_at = time.time()

    def total_rounds(self) -> int:
        return len(self.questions)

    def is_expired(self) -> bool:
        return (time.time() - self.last_active_at) > settings.session_ttl_minutes * 60


_LOCK = threading.RLock()
_SESSIONS: Dict[str, InterviewSession] = {}


def new_session(*, resume: dict, jd: dict, questions: List[InterviewQuestion]) -> InterviewSession:
    s = InterviewSession(resume=resume, jd=jd, questions=questions)
    with _LOCK:
        _SESSIONS[s.session_id] = s
    return s


def get_session(sid: str) -> Optional[InterviewSession]:
    with _LOCK:
        s = _SESSIONS.get(sid)
        if s is None:
            return None
        if s.is_expired() and not s.finished:
            _SESSIONS.pop(sid, None)
            return None
        return s


def delete_session(sid: str) -> bool:
    with _LOCK:
        return _SESSIONS.pop(sid, None) is not None


def stats() -> dict:
    with _LOCK:
        now = time.time()
        active = [s for s in _SESSIONS.values() if not s.finished and (now - s.last_active_at) < settings.session_ttl_minutes * 60]
        return {"total_sessions": len(_SESSIONS), "active_sessions": len(active)}
