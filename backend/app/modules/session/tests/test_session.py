"""会话模块单元测试。"""
from fastapi.testclient import TestClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup_interview(client: TestClient, enterprise_token: str) -> int:
    org = client.post("/api/v1/orgs", json={"name": "公司"}, headers=_auth(enterprise_token)).json()
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
        headers=_auth(enterprise_token),
    ).json()
    return iv["id"]


def test_start_session_creates_greeting(client: TestClient, enterprise_token: str, candidate_token: str):
    iid = _setup_interview(client, enterprise_token)
    r = client.post("/api/v1/sessions", json={"interview_id": iid}, headers=_auth(candidate_token))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "in_progress"

    msgs = client.get(f"/api/v1/sessions/{body['id']}/messages", headers=_auth(candidate_token)).json()
    assert len(msgs) == 1
    assert msgs[0]["role"] == "interviewer"


def test_start_session_requires_candidate(client: TestClient, enterprise_token: str):
    iid = _setup_interview(client, enterprise_token)
    r = client.post("/api/v1/sessions", json={"interview_id": iid}, headers=_auth(enterprise_token))
    assert r.status_code == 403


def test_start_session_interview_not_found(client: TestClient, candidate_token: str):
    r = client.post("/api/v1/sessions", json={"interview_id": 999}, headers=_auth(candidate_token))
    assert r.status_code == 404


def test_send_message_gets_ai_reply(client: TestClient, enterprise_token: str, candidate_token: str, llm):
    llm.reply = "请介绍一下你的项目经验。"
    iid = _setup_interview(client, enterprise_token)
    sid = client.post("/api/v1/sessions", json={"interview_id": iid}, headers=_auth(candidate_token)).json()["id"]

    r = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "我准备好了", "kind": "text"},
        headers=_auth(candidate_token),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "interviewer"
    assert r.json()["content"] == "请介绍一下你的项目经验。"
    assert len(llm.chat_calls) == 1

    msgs = client.get(f"/api/v1/sessions/{sid}/messages", headers=_auth(candidate_token)).json()
    assert len(msgs) == 3  # 开场 + 候选人 + AI


def test_send_message_empty_content(client: TestClient, enterprise_token: str, candidate_token: str):
    iid = _setup_interview(client, enterprise_token)
    sid = client.post("/api/v1/sessions", json={"interview_id": iid}, headers=_auth(candidate_token)).json()["id"]
    r = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "   ", "kind": "text"},
        headers=_auth(candidate_token),
    )
    assert r.status_code == 422


def test_other_candidate_cannot_access(client: TestClient, enterprise_token: str, candidate_token: str):
    iid = _setup_interview(client, enterprise_token)
    sid = client.post("/api/v1/sessions", json={"interview_id": iid}, headers=_auth(candidate_token)).json()["id"]

    # 注册第二个候选人
    other = client.post(
        "/api/v1/auth/candidate/register",
        json={"email": "c2@x.com", "password": "secret123", "name": "李四"},
    ).json()

    r = client.get(f"/api/v1/sessions/{sid}", headers=_auth(other["token"]))
    assert r.status_code == 403
