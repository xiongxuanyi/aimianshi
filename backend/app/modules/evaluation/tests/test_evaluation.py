"""评分模块单元测试。"""
from fastapi.testclient import TestClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _evaluation_reply() -> dict:
    return {
        "total_score": 82,
        "dimension_scores": {"专业技能": 85, "沟通表达": 78},
        "per_question": [{"question": "介绍项目", "comment": "条理清晰"}],
        "highlights": "逻辑清晰",
        "weaknesses": "表达可更精炼",
        "recommendation": "pass",
        "reason": "综合表现优秀",
    }


def test_evaluate_and_get(client: TestClient, enterprise_token: str, seeded_session_id: int, llm):
    llm.json_reply = _evaluation_reply()
    r = client.post(
        f"/api/v1/sessions/{seeded_session_id}/evaluate", headers=_auth(enterprise_token)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_score"] == 82
    assert body["recommendation"] == "pass"
    assert len(llm.json_calls) == 1

    r2 = client.get(
        f"/api/v1/sessions/{seeded_session_id}/evaluation", headers=_auth(enterprise_token)
    )
    assert r2.status_code == 200
    assert r2.json()["total_score"] == 82


def test_evaluate_session_not_found(client: TestClient, enterprise_token: str):
    r = client.post("/api/v1/sessions/999/evaluate", headers=_auth(enterprise_token))
    assert r.status_code == 404


def test_get_evaluation_not_found(client: TestClient, enterprise_token: str, seeded_session_id: int):
    r = client.get(
        f"/api/v1/sessions/{seeded_session_id}/evaluation", headers=_auth(enterprise_token)
    )
    assert r.status_code == 404
