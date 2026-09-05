"""评审模块单元测试。"""
from fastapi.testclient import TestClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_add_and_list_review(client: TestClient, enterprise_token: str, seeded_session_id: int):
    r = client.post(
        f"/api/v1/sessions/{seeded_session_id}/review",
        json={"decision": "pass", "note": "技术过硬"},
        headers=_auth(enterprise_token),
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "pass"

    r2 = client.get(
        f"/api/v1/sessions/{seeded_session_id}/reviews", headers=_auth(enterprise_token)
    )
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_add_review_invalid_decision(client: TestClient, enterprise_token: str, seeded_session_id: int):
    r = client.post(
        f"/api/v1/sessions/{seeded_session_id}/review",
        json={"decision": "maybe", "note": ""},
        headers=_auth(enterprise_token),
    )
    assert r.status_code == 422


def test_add_review_session_not_found(client: TestClient, enterprise_token: str):
    r = client.post(
        "/api/v1/sessions/999/review",
        json={"decision": "pass", "note": ""},
        headers=_auth(enterprise_token),
    )
    assert r.status_code == 404
