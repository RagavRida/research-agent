"""Pytest fixtures — spin up the FastAPI app against a throwaway SQLite DB."""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

# Ensure we can import the package and that settings load before app import.
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

os.environ.setdefault("TAVILY_API_KEY", "test-tavily")
os.environ.setdefault("JWT_SECRET", "pytest-secret")
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GOOGLE_API_KEY", "test-google")


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    """Fresh app + empty SQLite DB per test — full isolation."""
    db_path = tmp_path / f"test-{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    # Reload modules so the new DATABASE_URL is picked up.
    for mod in list(sys.modules):
        if (
            mod == "main"
            or mod.startswith("api.")
            or mod.startswith("db")
            or mod.startswith("services.auth")
            or mod == "config"
        ):
            sys.modules.pop(mod, None)

    from main import app  # noqa: E402  (imported late on purpose)

    with TestClient(app) as c:
        yield c
