# ---------------------------------------------------------------------------
# test_api.py — API integration tests using FastAPI TestClient
# ---------------------------------------------------------------------------
import pytest
from fastapi.testclient import TestClient

from src.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    def test_health_shows_local_mode(self, monkeypatch, client):
        """Health mode reflects config — accept whatever the current env yields."""
        response = client.get("/health")
        assert response.json()["mode"] in ("local", "foundry")


class TestRootEndpoint:
    def test_root_returns_info(self, client):
        response = client.get("/")
        assert response.status_code == 200
        # Root serves the UI (HTML) when static files exist, or JSON otherwise
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            assert "Incident Triage Copilot" in response.text
        else:
            data = response.json()
            assert data["name"] == "Incident Triage Copilot"


class TestTriageEndpoint:
    def test_triage_basic_query(self, client):
        response = client.post(
            "/triage",
            json={"message": "Our API is returning 500 errors"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "correlation_id" in data
        assert len(data["summary"]) > 0
        assert len(data["results"]) > 0

    def test_triage_with_context(self, client):
        response = client.post(
            "/triage",
            json={
                "message": "Debug this error and suggest a fix",
                "context": {
                    "log_data": "2025-01-15 ERROR NullPointerException at line 42"
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["specialists_invoked"]) >= 2

    def test_triage_preserves_correlation_id(self, client):
        response = client.post(
            "/triage",
            json={
                "message": "Test query",
                "correlation_id": "my-trace-id-999",
            },
        )
        assert response.status_code == 200
        assert response.json()["correlation_id"] == "my-trace-id-999"

    def test_triage_empty_message_returns_422(self, client):
        response = client.post("/triage", json={"message": ""})
        assert response.status_code == 422
