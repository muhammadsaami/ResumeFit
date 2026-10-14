"""Health endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

HEALTH_URL = "/api/v1/health"


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get(HEALTH_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"]
    assert body["version"]
    assert body["uptime_seconds"] >= 0
    assert isinstance(body["stored_resumes"], int)
    assert "timestamp" in body
