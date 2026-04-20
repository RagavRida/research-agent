from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "timestamp" in body


def test_agent_config_exposes_threshold(client: TestClient) -> None:
    r = client.get("/api/agent/config")
    assert r.status_code == 200
    body = r.json()
    assert body["confidence_threshold"] >= 0
    assert body["max_iterations"] >= 1
