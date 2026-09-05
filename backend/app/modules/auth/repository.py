"""认证模块数据访问层。"""
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, email: str, hashed_password: str, user_type: str, name: str) -> User:
        user = User(email=email, hashed_password=hashed_password, user_type=user_type, name=name)
        db.add(user)
        db.flush()
        return user
