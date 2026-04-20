"""Tests for /api/history — list, detail, delete, auth-gating.

Research runs themselves are not exercised here (they would require a real
Tavily + LLM). We insert Query rows directly through the same async session
factory the app uses, then hit the routes.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient


def _signup_and_auth(client: TestClient, email="hist@example.com"):
    r = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "supersecret1", "name": "Hist"},
    )
    assert r.status_code == 201
    body = r.json()
    return body["token"], body["user"]["id"]


def _insert_query(user_id: str, query: str, confidence: float = 90.0) -> str:
    """Persist a Query row directly via the app's async SessionLocal."""
    from db import SessionLocal  # type: ignore
    from db.models import Query as QueryRow

    async def _do() -> str:
        async with SessionLocal() as session:
            row = QueryRow(
                user_id=user_id,
                query=query,
                run_id="test1234",
                final_answer="Synthetic answer.",
                confidence=confidence,
                iterations=2,
                duration_ms=1234.5,
                citations=[{"id": 1, "url": "https://example.com"}],
                caveats=["test caveat"],
                contradictions=[],
            )
            session.add(row)
            await session.commit()
            return row.id

    return asyncio.get_event_loop().run_until_complete(_do())


def test_history_requires_auth(client: TestClient) -> None:
    r = client.get("/api/history")
    assert r.status_code == 401


def test_history_returns_empty_for_new_user(client: TestClient) -> None:
    token, _ = _signup_and_auth(client)
    r = client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_history_list_and_isolation(client: TestClient) -> None:
    a_token, a_id = _signup_and_auth(client, email="a@example.com")
    b_token, b_id = _signup_and_auth(client, email="b@example.com")

    _insert_query(a_id, "alpha question", confidence=80)
    _insert_query(a_id, "second alpha", confidence=95)
    _insert_query(b_id, "beta question", confidence=70)

    a = client.get("/api/history", headers={"Authorization": f"Bearer {a_token}"}).json()
    assert len(a) == 2
    assert {item["query"] for item in a} == {"alpha question", "second alpha"}

    b = client.get("/api/history", headers={"Authorization": f"Bearer {b_token}"}).json()
    assert len(b) == 1
    assert b[0]["query"] == "beta question"


def test_history_detail_404_for_other_users_row(client: TestClient) -> None:
    a_token, a_id = _signup_and_auth(client, email="a@example.com")
    b_token, b_id = _signup_and_auth(client, email="b@example.com")
    a_row = _insert_query(a_id, "my private query")

    # A sees it
    r = client.get(
        f"/api/history/{a_row}", headers={"Authorization": f"Bearer {a_token}"}
    )
    assert r.status_code == 200
    assert r.json()["final_answer"] == "Synthetic answer."
    assert r.json()["citations"][0]["url"] == "https://example.com"

    # B does not
    r = client.get(
        f"/api/history/{a_row}", headers={"Authorization": f"Bearer {b_token}"}
    )
    assert r.status_code == 404


def test_history_delete_removes_row(client: TestClient) -> None:
    token, uid = _signup_and_auth(client)
    row_id = _insert_query(uid, "to delete")

    r = client.delete(f"/api/history/{row_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204

    r = client.get(f"/api/history/{row_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_history_pagination(client: TestClient) -> None:
    token, uid = _signup_and_auth(client)
    for i in range(5):
        _insert_query(uid, f"q{i}")

    page1 = client.get(
        "/api/history?limit=2&offset=0", headers={"Authorization": f"Bearer {token}"}
    ).json()
    page2 = client.get(
        "/api/history?limit=2&offset=2", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert len(page1) == 2
    assert len(page2) == 2
    assert {p["id"] for p in page1}.isdisjoint({p["id"] for p in page2})
