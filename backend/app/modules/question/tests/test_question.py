"""题库模块单元测试。"""
from fastapi.testclient import TestClient

from app.models.interview import QuestionTemplate


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_template(session_factory) -> QuestionTemplate:
    db = session_factory()
    t = QuestionTemplate(
        title="Java 后端通用",
        industry="互联网",
        position="Java 后端工程师",
        dimensions=["专业技能"],
        questions=[{"question": "介绍项目", "hint": "", "dimension": "专业技能"}],
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    db.close()
    return t


def test_list_templates(client: TestClient, enterprise_token: str, session_factory):
    _seed_template(session_factory)
    r = client.get("/api/v1/templates", headers=_auth(enterprise_token))
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["position"] == "Java 后端工程师"


def test_get_template(client: TestClient, enterprise_token: str, session_factory):
    t = _seed_template(session_factory)
    r = client.get(f"/api/v1/templates/{t.id}", headers=_auth(enterprise_token))
    assert r.status_code == 200
    assert r.json()["id"] == t.id


def test_get_template_not_found(client: TestClient, enterprise_token: str):
    r = client.get("/api/v1/templates/999", headers=_auth(enterprise_token))
    assert r.status_code == 404


def test_generate_questions(client: TestClient, enterprise_token: str, llm):
    llm.json_reply = {
        "dimensions": ["专业技能"],
        "questions": [{"question": "请介绍你的项目经验", "hint": "关注难点", "dimension": "专业技能"}],
    }
    r = client.post(
        "/api/v1/interviews/generate-questions",
        json={"jd": "需要会 Python"},
        headers=_auth(enterprise_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["questions"][0]["question"] == "请介绍你的项目经验"
    assert len(llm.json_calls) == 1


def test_generate_questions_empty_jd(client: TestClient, enterprise_token: str):
    r = client.post(
        "/api/v1/interviews/generate-questions",
        json={"jd": "   "},
        headers=_auth(enterprise_token),
    )
    assert r.status_code == 422
