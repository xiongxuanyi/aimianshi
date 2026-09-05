"""组织模块单元测试。"""
from fastapi.testclient import TestClient


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_create_org(client: TestClient, enterprise_token: str):
    r = client.post("/api/v1/orgs", json={"name": "示例公司"}, headers=_auth(enterprise_token))
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "示例公司"
    assert body["id"] > 0


def test_create_org_requires_enterprise(client: TestClient, candidate_token: str):
    r = client.post("/api/v1/orgs", json={"name": "x"}, headers=_auth(candidate_token))
    assert r.status_code == 403


def test_add_member_and_list(client: TestClient, enterprise_token: str):
    org = client.post("/api/v1/orgs", json={"name": "示例公司"}, headers=_auth(enterprise_token)).json()
    client.post(
        "/api/v1/auth/register",
        json={"email": "hr2@corp.com", "password": "secret123", "name": "HR2"},
    )
    r = client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "hr2@corp.com", "role": "hr"},
        headers=_auth(enterprise_token),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "hr"
    assert r.json()["user_email"] == "hr2@corp.com"

    r2 = client.get(f"/api/v1/orgs/{org['id']}/members", headers=_auth(enterprise_token))
    assert r2.status_code == 200
    assert len(r2.json()) == 2  # 创建者 admin + 新增 hr


def test_add_member_invalid_role(client: TestClient, enterprise_token: str):
    org = client.post("/api/v1/orgs", json={"name": "示例公司"}, headers=_auth(enterprise_token)).json()
    client.post(
        "/api/v1/auth/register",
        json={"email": "hr2@corp.com", "password": "secret123", "name": "HR2"},
    )
    r = client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "hr2@corp.com", "role": "boss"},
        headers=_auth(enterprise_token),
    )
    assert r.status_code == 422


def test_list_members_org_not_found(client: TestClient, enterprise_token: str):
    r = client.get("/api/v1/orgs/999/members", headers=_auth(enterprise_token))
    assert r.status_code == 404
