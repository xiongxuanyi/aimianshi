"""认证模块业务逻辑。"""
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.modules.auth.repository import UserRepository


class AuthService:
    def __init__(self, repo: UserRepository | None = None):
        self.repo = repo or UserRepository()

    def _issue(self, user: User) -> tuple[str, User]:
        token = create_access_token(str(user.id), user.user_type)
        return token, user

    def register(self, db: Session, email: str, password: str, name: str, user_type: str) -> tuple[str, User]:
        if self.repo.get_by_email(db, email):
            raise ConflictError("该邮箱已注册")
        user = self.repo.create(db, email, hash_password(password), user_type, name)
        db.commit()
        db.refresh(user)
        return self._issue(user)

    def login(self, db: Session, email: str, password: str, user_type: str) -> tuple[str, User]:
        user = self.repo.get_by_email(db, email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("邮箱或密码错误")
        if user.user_type != user_type:
            raise ForbiddenError("账户类型不匹配，请使用正确的入口登录")
        return self._issue(user)
