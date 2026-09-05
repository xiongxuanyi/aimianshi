"""组织模块数据访问层。"""
from sqlalchemy.orm import Session

from app.models.organization import Membership, Organization
from app.models.user import User


class OrgRepository:
    def create(self, db: Session, name: str) -> Organization:
        org = Organization(name=name)
        db.add(org)
        db.flush()
        return org

    def get(self, db: Session, org_id: int) -> Organization | None:
        return db.get(Organization, org_id)

    def add_membership(self, db: Session, org_id: int, user_id: int, role: str) -> Membership:
        m = Membership(org_id=org_id, user_id=user_id, role=role)
        db.add(m)
        db.flush()
        return m

    def list_members(self, db: Session, org_id: int) -> list[tuple[Membership, User]]:
        return (
            db.query(Membership, User)
            .join(User, Membership.user_id == User.id)
            .filter(Membership.org_id == org_id)
            .all()
        )
