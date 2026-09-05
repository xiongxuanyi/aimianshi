"""邀请模块路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_enterprise
from app.models.user import User
from app.modules.invitation.schemas import InvitationOut, InvitationValidateOut
from app.modules.invitation.service import InvitationService

router = APIRouter(tags=["invitation"])
service = InvitationService()


@router.post("/interviews/{interview_id}/invite", response_model=InvitationOut)
def invite(
    interview_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(require_enterprise),
):
    return service.create(db, interview_id, me.id)


@router.get("/invitations/{token}", response_model=InvitationValidateOut)
def validate(token: str, db: Session = Depends(get_db)):
    inv = service.validate(db, token)
    return {"interview_id": inv.interview_id, "valid": True}
