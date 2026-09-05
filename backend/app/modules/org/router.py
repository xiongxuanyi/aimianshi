"""组织模块路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_enterprise
from app.models.user import User
from app.modules.org.schemas import MemberIn, MemberOut, OrgIn, OrgOut
from app.modules.org.service import OrgService

router = APIRouter(prefix="/orgs", tags=["org"])
service = OrgService()


@router.post("", response_model=OrgOut)
def create_org(body: OrgIn, db: Session = Depends(get_db), me: User = Depends(require_enterprise)):
    return service.create_org(db, body.name, me.id)


@router.get("/{org_id}/members", response_model=list[MemberOut])
def list_members(org_id: int, db: Session = Depends(get_db), me: User = Depends(require_enterprise)):
    rows = service.list_members(db, org_id)
    return [
        {
            "id": m.id,
            "org_id": m.org_id,
            "user_id": m.user_id,
            "role": m.role,
            "user_name": u.name,
            "user_email": u.email,
        }
        for m, u in rows
    ]


@router.post("/{org_id}/members", response_model=MemberOut)
def add_member(
    org_id: int,
    body: MemberIn,
    db: Session = Depends(get_db),
    me: User = Depends(require_enterprise),
):
    m, u = service.add_member(db, org_id, body.email, body.role)
    return {
        "id": m.id,
        "org_id": m.org_id,
        "user_id": m.user_id,
        "role": m.role,
        "user_name": u.name,
        "user_email": u.email,
    }
