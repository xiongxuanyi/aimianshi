"""FastAPI 依赖：当前用户、LLM 客户端、角色校验。"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.llm.base import LLMClient
from app.llm.deepseek import DeepSeekLLMClient
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError()
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise UnauthorizedError("token 无效或已过期")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None:
        raise UnauthorizedError("用户不存在")
    return user


def require_enterprise(user: User = Depends(get_current_user)) -> User:
    if user.user_type != "enterprise":
        raise ForbiddenError("仅企业用户可访问")
    return user


def require_candidate(user: User = Depends(get_current_user)) -> User:
    if user.user_type != "candidate":
        raise ForbiddenError("仅候选人可访问")
    return user


def get_llm() -> LLMClient:
    """LLM 客户端依赖（测试中通过 dependency_overrides 替换为 Fake）。"""
    return DeepSeekLLMClient()
