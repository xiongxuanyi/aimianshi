"""FastAPI 应用入口。"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.modules.auth.router import router as auth_router
from app.modules.org.router import router as org_router
from app.modules.question.router import router as question_router
from app.modules.interview.router import router as interview_router
from app.modules.session.router import router as session_router
from app.modules.evaluation.router import router as evaluation_router
from app.modules.review.router import router as review_router
from app.modules.invitation.router import router as invitation_router

app = FastAPI(title="AI 面试官", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "detail": exc.message})


API = "/api/v1"
app.include_router(auth_router, prefix=API)
app.include_router(org_router, prefix=API)
app.include_router(question_router, prefix=API)
app.include_router(interview_router, prefix=API)
app.include_router(session_router, prefix=API)
app.include_router(evaluation_router, prefix=API)
app.include_router(review_router, prefix=API)
app.include_router(invitation_router, prefix=API)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
