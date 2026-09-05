"""邀请模块单元测试。"""
from fastapi.testclient import TestClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_interview(client: TestClient, enterprise_token: str) -> int:
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


def test_create_and_validate_invite(client: TestClient, enterprise_token: str):
    iid = _create_interview(client, enterprise_token)
    r = client.post(f"/api/v1/interviews/{iid}/invite", headers=_auth(enterprise_token))
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["url"].endswith(body["token"])

    r2 = client.get(f"/api/v1/invitations/{body['token']}")
    assert r2.status_code == 200
    assert r2.json()["interview_id"] == iid
    assert r2.json()["valid"] is True


def test_create_invite_interview_not_found(client: TestClient, enterprise_token: str):
    r = client.post("/api/v1/interviews/999/invite", headers=_auth(enterprise_token))
    assert r.status_code == 404


def test_validate_invalid_token(client: TestClient):
    r = client.get("/api/v1/invitations/nonexistent-token")
    assert r.status_code == 404
