# ---------------------------------------------------------------------------
# test_routing.py — Unit tests for coordinator routing logic
# ---------------------------------------------------------------------------
# Validates that the coordinator correctly routes queries to specialists
# based on keyword detection and context signals.
# ---------------------------------------------------------------------------
import pytest

from src.agents.coordinator import _detect_specialists
from src.models import AgentRole


class TestRoutingLogic:
    """Test the coordinator's specialist routing decisions."""

    def test_simple_query_routes_to_research_only(self):
        """A simple query with no diagnostic/remediation signals → Research only."""
        specialists = _detect_specialists("API is slow", None)
        assert specialists == [AgentRole.RESEARCH]

    def test_error_query_routes_to_research_and_diagnostics(self):
        """A query mentioning errors → Research + Diagnostics."""
        specialists = _detect_specialists(
            "Getting 500 errors on the payment endpoint", None
        )
        assert AgentRole.RESEARCH in specialists
        assert AgentRole.DIAGNOSTICS in specialists

    def test_fix_query_routes_to_research_and_remediation(self):
        """A query asking for a fix → Research + Remediation."""
        specialists = _detect_specialists(
            "How do I fix the authentication timeout?", None
        )
        assert AgentRole.RESEARCH in specialists
        assert AgentRole.REMEDIATION in specialists

    def test_comprehensive_query_routes_to_all(self):
        """A query with both diagnostic and remediation signals → all three."""
        specialists = _detect_specialists(
            "We're seeing 503 errors in the logs. Need a runbook to fix this.", None
        )
        assert AgentRole.RESEARCH in specialists
        assert AgentRole.DIAGNOSTICS in specialists
        assert AgentRole.REMEDIATION in specialists

    def test_log_data_in_context_triggers_diagnostics(self):
        """Providing log_data in context → Diagnostics is added."""
        context = {"log_data": "2025-01-15 ERROR NullPointerException..."}
        specialists = _detect_specialists("What happened?", context)
        assert AgentRole.DIAGNOSTICS in specialists

    def test_long_query_gets_all_specialists(self):
        """A long, complex query (>15 words) with only general terms → all three."""
        long_query = (
            "Our main production web application has been experiencing intermittent "
            "issues since this morning and multiple customers have reported problems "
            "with their dashboard loading times being significantly degraded"
        )
        specialists = _detect_specialists(long_query, None)
        assert AgentRole.RESEARCH in specialists
        assert AgentRole.DIAGNOSTICS in specialists
        assert AgentRole.REMEDIATION in specialists

    def test_research_is_always_first(self):
        """Research agent is always the first specialist invoked."""
        for query in [
            "simple query",
            "error in logs need to diagnose",
            "fix the deployment",
        ]:
            specialists = _detect_specialists(query, None)
            assert specialists[0] == AgentRole.RESEARCH

    def test_rollback_triggers_remediation(self):
        """Rollback keyword → Remediation."""
        specialists = _detect_specialists("Need to rollback the last deploy", None)
        assert AgentRole.REMEDIATION in specialists

    def test_stack_trace_triggers_diagnostics(self):
        """Stack trace keyword → Diagnostics."""
        specialists = _detect_specialists(
            "Here is the stack trace from the crash", None
        )
        assert AgentRole.DIAGNOSTICS in specialists

    def test_oom_triggers_diagnostics(self):
        """OOM keyword → Diagnostics."""
        specialists = _detect_specialists(
            "Pod keeps getting killed with OOM", None
        )
        assert AgentRole.DIAGNOSTICS in specialists

    def test_no_duplicate_specialists(self):
        """Each specialist appears at most once."""
        specialists = _detect_specialists(
            "error error error fix fix fix", None
        )
        assert len(specialists) == len(set(specialists))
