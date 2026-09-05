"""面试配置模块业务逻辑。"""
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.interview import Interview
from app.modules.interview.repository import InterviewRepository
from app.modules.org.repository import OrgRepository

VALID_STATUS = {"draft", "published", "closed"}
VALID_SOURCE = {"template", "jd_generated"}


class InterviewService:
    def __init__(
        self,
        repo: InterviewRepository | None = None,
        org_repo: OrgRepository | None = None,
    ):
        self.repo = repo or InterviewRepository()
        self.org_repo = org_repo or OrgRepository()

    def create(self, db: Session, data: dict, created_by: int) -> Interview:
        if self.org_repo.get(db, data["org_id"]) is None:
            raise NotFoundError("组织", str(data["org_id"]))
        if data["question_source"] not in VALID_SOURCE:
            raise ValidationError("题目来源只能是 template 或 jd_generated")
        if not data.get("questions"):
            raise ValidationError("面试题目不能为空")
        iv = self.repo.create(db, **data, created_by=created_by)
        db.commit()
        db.refresh(iv)
        return iv

    def list_interviews(self, db: Session, org_id: int | None = None) -> list[Interview]:
        if org_id is not None:
            return self.repo.list_by_org(db, org_id)
        return self.repo.list_all(db)

    def get(self, db: Session, interview_id: int) -> Interview:
        iv = self.repo.get(db, interview_id)
        if iv is None:
            raise NotFoundError("面试", str(interview_id))
        return iv

    def update_status(self, db: Session, interview_id: int, status: str) -> Interview:
        iv = self.get(db, interview_id)
        if status not in VALID_STATUS:
            raise ValidationError("非法状态")
        iv.status = status
        db.commit()
        db.refresh(iv)
        return iv
