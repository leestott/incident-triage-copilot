# ---------------------------------------------------------------------------
# test_models.py — Unit tests for data models
# ---------------------------------------------------------------------------
import pytest
from pydantic import ValidationError

from src.models import AgentRole, TriageRequest, TriageResponse, AgentResult


class TestTriageRequest:
    def test_valid_request(self):
        req = TriageRequest(message="API is down")
        assert req.message == "API is down"
        assert req.correlation_id is None

    def test_with_correlation_id(self):
        req = TriageRequest(message="test", correlation_id="abc-123")
        assert req.correlation_id == "abc-123"

    def test_with_context(self):
        req = TriageRequest(message="test", context={"log_data": "some logs"})
        assert req.context["log_data"] == "some logs"

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            TriageRequest(message="")


class TestTriageResponse:
    def test_valid_response(self):
        resp = TriageResponse(
            correlation_id="test-123",
            summary="All good",
            specialists_invoked=[AgentRole.RESEARCH],
            results=[],
            turn_count=1,
        )
        assert resp.correlation_id == "test-123"

    def test_default_fields(self):
        resp = TriageResponse(correlation_id="x", summary="s")
        assert resp.specialists_invoked == []
        assert resp.results == []
        assert resp.turn_count == 0


class TestAgentResult:
    def test_valid_result(self):
        result = AgentResult(
            agent=AgentRole.RESEARCH,
            content="Found relevant info",
            confidence=0.85,
            tools_used=["bing_grounding"],
        )
        assert result.confidence == 0.85

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            AgentResult(agent=AgentRole.RESEARCH, content="x", confidence=1.5)

        with pytest.raises(ValidationError):
            AgentResult(agent=AgentRole.RESEARCH, content="x", confidence=-0.1)
