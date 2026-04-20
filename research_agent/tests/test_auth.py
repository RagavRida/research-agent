"""End-to-end tests for /api/auth/*."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _signup(client: TestClient, email="ada@example.com", password="supersecret1", name="Ada"):
    return client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "name": name},
    )


def test_signup_creates_user_and_returns_token(client: TestClient) -> None:
    r = _signup(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "token" in body and isinstance(body["token"], str) and body["token"]
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["name"] == "Ada"
    assert "id" in body["user"]


def test_signup_rejects_duplicate_email(client: TestClient) -> None:
    _signup(client)
    r = _signup(client)
    assert r.status_code == 409
    assert "exists" in r.json()["detail"].lower()


def test_signup_rejects_short_password(client: TestClient) -> None:
    r = _signup(client, password="short")
    assert r.status_code == 422


def test_signin_returns_fresh_token(client: TestClient) -> None:
    _signup(client)
    r = client.post(
        "/api/auth/signin",
        json={"email": "ada@example.com", "password": "supersecret1"},
    )
    assert r.status_code == 200
    assert r.json()["token"]


def test_signin_wrong_password_is_401(client: TestClient) -> None:
    _signup(client)
    r = client.post(
        "/api/auth/signin",
        json={"email": "ada@example.com", "password": "WRONG"},
    )
    assert r.status_code == 401


def test_signin_unknown_email_is_401(client: TestClient) -> None:
    r = client.post(
        "/api/auth/signin",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert r.status_code == 401


def test_me_requires_bearer(client: TestClient) -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_rejects_garbage_token(client: TestClient) -> None:
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    token = _signup(client).json()["token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == "ada@example.com"
    assert me["name"] == "Ada"


def test_email_is_lowercased_on_signup(client: TestClient) -> None:
    r = _signup(client, email="MixedCase@Example.COM")
    assert r.status_code == 201
    # can sign in with the lower-cased form
    r2 = client.post(
        "/api/auth/signin",
        json={"email": "mixedcase@example.com", "password": "supersecret1"},
    )
    assert r2.status_code == 200
