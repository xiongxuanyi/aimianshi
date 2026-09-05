"""组织模块业务逻辑。"""
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.organization import Membership, Organization
from app.models.user import User
from app.modules.auth.repository import UserRepository
from app.modules.org.repository import OrgRepository

VALID_ROLES = {"admin", "hr"}


class OrgService:
    def __init__(self, repo: OrgRepository | None = None, user_repo: UserRepository | None = None):
        self.repo = repo or OrgRepository()
        self.user_repo = user_repo or UserRepository()

    def create_org(self, db: Session, name: str, creator_id: int) -> Organization:
        org = self.repo.create(db, name)
        self.repo.add_membership(db, org.id, creator_id, "admin")
        db.commit()
        db.refresh(org)
        return org

    def list_members(self, db: Session, org_id: int) -> list[tuple[Membership, User]]:
        if self.repo.get(db, org_id) is None:
            raise NotFoundError("组织", str(org_id))
        return self.repo.list_members(db, org_id)

    def add_member(self, db: Session, org_id: int, email: str, role: str) -> tuple[Membership, User]:
        if self.repo.get(db, org_id) is None:
            raise NotFoundError("组织", str(org_id))
        if role not in VALID_ROLES:
            raise ValidationError("角色只能是 admin 或 hr")
        user = self.user_repo.get_by_email(db, email)
        if user is None or user.user_type != "enterprise":
            raise ValidationError("该用户不是企业用户")
        m = self.repo.add_membership(db, org_id, user.id, role)
        db.commit()
        db.refresh(m)
        return m, user
