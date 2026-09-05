"""共享测试夹具：内存 SQLite、TestClient、FakeLLM、用户 token。"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_llm
from app.core.security import create_access_token, hash_password
from app.llm.fake import FakeLLMClient
from app.main import app
from app.models.user import User


@pytest.fixture
def engine():
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(e)
    yield e
    e.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def llm():
    return FakeLLMClient()


@pytest.fixture
def client(engine, session_factory, llm):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm] = lambda: llm
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def enterprise_token(session_factory):
    db = session_factory()
    user = User(
        email="hr@corp.com",
        hashed_password=hash_password("secret123"),
        user_type="enterprise",
        name="HR",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return create_access_token(str(user.id), "enterprise")


@pytest.fixture
def candidate_token(session_factory):
    db = session_factory()
    user = User(
        email="c@x.com",
        hashed_password=hash_password("secret123"),
        user_type="candidate",
        name="张三",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return create_access_token(str(user.id), "candidate")


@pytest.fixture
def seeded_session_id(client, enterprise_token, candidate_token):
    """创建 组织 -> 面试 -> 会话，返回会话 ID。"""
    h = {"Authorization": f"Bearer {enterprise_token}"}
    org = client.post("/api/v1/orgs", json={"name": "公司"}, headers=h).json()
    iv = client.post(
        "/api/v1/interviews",
        json={
            "org_id": org["id"],
            "title": "Java 初筛",
            "position": "Java 后端工程师",
            "jd": "",
            "question_source": "template",
            "questions": [{"question": "介绍项目", "hint": "", "dimension": "专业技能"}],
            "dimension_weights": {"专业技能": 0.6},
            "pass_thresholds": {"pass": 75, "pending": 60},
        },
        headers=h,
    ).json()
    ch = {"Authorization": f"Bearer {candidate_token}"}
    return client.post("/api/v1/sessions", json={"interview_id": iv["id"]}, headers=ch).json()["id"]
