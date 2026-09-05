"""认证模块路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
service = AuthService()


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    token, user = service.register(db, body.email, body.password, body.name, "enterprise")
    return {"token": token, "user_type": user.user_type, "user": user}


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    token, user = service.login(db, body.email, body.password, "enterprise")
    return {"token": token, "user_type": user.user_type, "user": user}


@router.post("/candidate/register", response_model=TokenOut)
def candidate_register(body: RegisterIn, db: Session = Depends(get_db)):
    token, user = service.register(db, body.email, body.password, body.name, "candidate")
    return {"token": token, "user_type": user.user_type, "user": user}


@router.post("/candidate/login", response_model=TokenOut)
def candidate_login(body: LoginIn, db: Session = Depends(get_db)):
    token, user = service.login(db, body.email, body.password, "candidate")
    return {"token": token, "user_type": user.user_type, "user": user}
