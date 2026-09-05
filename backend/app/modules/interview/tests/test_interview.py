"""面试配置模块单元测试。"""
from fastapi.testclient import TestClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_org(client: TestClient, token: str) -> dict:
    return client.post("/api/v1/orgs", json={"name": "示例公司"}, headers=_auth(token)).json()


def _payload(org_id: int) -> dict:
    return {
        "org_id": org_id,
        "title": "Java 初筛",
        "position": "Java 后端工程师",
        "jd": "",
        "question_source": "template",
        "questions": [{"question": "介绍项目", "hint": "", "dimension": "专业技能"}],
        "dimension_weights": {"专业技能": 0.6, "沟通表达": 0.4},
        "pass_thresholds": {"pass": 75, "pending": 60},
    }


def test_create_interview(client: TestClient, enterprise_token: str):
    org = _create_org(client, enterprise_token)
    r = client.post("/api/v1/interviews", json=_payload(org["id"]), headers=_auth(enterprise_token))
    assert r.status_code == 200
    assert r.json()["status"] == "draft"
    assert r.json()["title"] == "Java 初筛"


def test_create_interview_org_not_found(client: TestClient, enterprise_token: str):
    r = client.post("/api/v1/interviews", json=_payload(999), headers=_auth(enterprise_token))
    assert r.status_code == 404


def test_create_interview_invalid_source(client: TestClient, enterprise_token: str):
    org = _create_org(client, enterprise_token)
    p = _payload(org["id"])
    p["question_source"] = "magic"
    r = client.post("/api/v1/interviews", json=p, headers=_auth(enterprise_token))
    assert r.status_code == 422


def test_list_and_get_interview(client: TestClient, enterprise_token: str):
    org = _create_org(client, enterprise_token)
    iv = client.post("/api/v1/interviews", json=_payload(org["id"]), headers=_auth(enterprise_token)).json()
    r = client.get("/api/v1/interviews", params={"org_id": org["id"]}, headers=_auth(enterprise_token))
    assert r.status_code == 200
    assert len(r.json()) == 1

    r2 = client.get(f"/api/v1/interviews/{iv['id']}", headers=_auth(enterprise_token))
    assert r2.status_code == 200
    assert r2.json()["title"] == "Java 初筛"


def test_get_interview_not_found(client: TestClient, enterprise_token: str):
    r = client.get("/api/v1/interviews/999", headers=_auth(enterprise_token))
    assert r.status_code == 404


def test_update_status(client: TestClient, enterprise_token: str):
    org = _create_org(client, enterprise_token)
    iv = client.post("/api/v1/interviews", json=_payload(org["id"]), headers=_auth(enterprise_token)).json()
    r = client.patch(
        f"/api/v1/interviews/{iv['id']}/status",
        json={"status": "published"},
        headers=_auth(enterprise_token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "published"
