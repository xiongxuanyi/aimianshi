"""认证模块单元测试。"""
from fastapi.testclient import TestClient


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_enterprise_register_and_login(client: TestClient):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "hr@corp.com", "password": "secret123", "name": "HR"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["user_type"] == "enterprise"
    assert body["token"]
    assert body["user"]["email"] == "hr@corp.com"

    r2 = client.post(
        "/api/v1/auth/login",
        json={"email": "hr@corp.com", "password": "secret123"},
    )
    assert r2.status_code == 200
    assert r2.json()["token"]
    assert r2.json()["user_type"] == "enterprise"


def test_register_duplicate_email_conflict(client: TestClient):
    payload = {"email": "hr@corp.com", "password": "secret123", "name": "HR"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 200
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


def test_login_wrong_password_unauthorized(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "hr@corp.com", "password": "secret123", "name": "HR"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "hr@corp.com", "password": "wrongpass"},
    )
    assert r.status_code == 401


def test_candidate_register_and_login(client: TestClient):
    r = client.post(
        "/api/v1/auth/candidate/register",
        json={"email": "c@x.com", "password": "secret123", "name": "张三"},
    )
    assert r.status_code == 200
    assert r.json()["user_type"] == "candidate"

    r2 = client.post(
        "/api/v1/auth/candidate/login",
        json={"email": "c@x.com", "password": "secret123"},
    )
    assert r2.status_code == 200
    assert r2.json()["user_type"] == "candidate"


def test_candidate_cannot_login_enterprise(client: TestClient):
    client.post(
        "/api/v1/auth/candidate/register",
        json={"email": "c@x.com", "password": "secret123", "name": "张三"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "c@x.com", "password": "secret123"},
    )
    assert r.status_code == 403
