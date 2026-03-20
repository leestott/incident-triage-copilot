# ---------------------------------------------------------------------------
# test_coordinator.py — Integration test for the full triage pipeline
# ---------------------------------------------------------------------------
import pytest

from src.agents.coordinator import Coordinator
from src.models import AgentRole, TriageRequest


class TestCoordinator:
    @pytest.fixture
    def coordinator(self):
        return Coordinator()

    @pytest.mark.asyncio
    async def test_basic_triage(self, coordinator):
        """End-to-end local triage with a simple query."""
        request = TriageRequest(message="Our API is returning 500 errors since 2pm")
        response = await coordinator.triage(request, client=None)

        assert response.correlation_id.startswith("triage-")
        assert len(response.results) > 0
        assert response.turn_count > 0
        assert len(response.summary) > 0

    @pytest.mark.asyncio
    async def test_respects_correlation_id(self, coordinator):
        """User-provided correlation IDs are preserved."""
        request = TriageRequest(
            message="Debug this error",
            correlation_id="custom-id-123",
        )
        response = await coordinator.triage(request, client=None)
        assert response.correlation_id == "custom-id-123"

    @pytest.mark.asyncio
    async def test_full_pipeline_with_context(self, coordinator):
        """Triage with log_data context triggers all three specialists."""
        request = TriageRequest(
            message="Getting OOM errors, need a fix. Here are the logs.",
            context={
                "log_data": (
                    "2025-01-15T10:00:00Z ERROR OutOfMemoryError\n"
                    "2025-01-15T10:00:01Z FATAL JVM heap exhausted\n"
                )
            },
        )
        response = await coordinator.triage(request, client=None)

        invoked_roles = set(response.specialists_invoked)
        assert AgentRole.RESEARCH in invoked_roles
        assert AgentRole.DIAGNOSTICS in invoked_roles
        assert AgentRole.REMEDIATION in invoked_roles
        assert response.turn_count == 3

    @pytest.mark.asyncio
    async def test_max_turns_limit(self, coordinator):
        """Max turns limit is respected."""
        request = TriageRequest(
            message="Major outage: logs show errors, need immediate fix and rollback plan"
        )
        response = await coordinator.triage(request, client=None, max_turns=1)
        assert response.turn_count <= 1

    @pytest.mark.asyncio
    async def test_summary_includes_correlation_id(self, coordinator):
        """The summary includes the correlation ID for traceability."""
        request = TriageRequest(message="Service is degraded")
        response = await coordinator.triage(request, client=None)
        assert response.correlation_id in response.summary
