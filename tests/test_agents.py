# ---------------------------------------------------------------------------
# test_agents.py — Unit tests for specialist agents (local mode)
# ---------------------------------------------------------------------------
import pytest

from src.agents.diagnostics_agent import DiagnosticsAgent
from src.agents.remediation_agent import RemediationAgent
from src.agents.research_agent import ResearchAgent
from src.models import AgentRole


@pytest.fixture
def shared_context():
    return {"original_query": "test query", "model_deployment": "gpt-4o"}


class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_local_mode_returns_result(self, shared_context):
        agent = ResearchAgent()
        result = await agent.run(
            query="API returning 500 errors",
            shared_context=shared_context,
            correlation_id="test-001",
            client=None,  # local mode
        )
        assert result.agent == AgentRole.RESEARCH
        assert "local_heuristic" in result.tools_used
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_shares_findings_in_context(self, shared_context):
        agent = ResearchAgent()
        await agent.run(
            query="database connection timeout",
            shared_context=shared_context,
            correlation_id="test-002",
            client=None,
        )
        assert "research_findings" in shared_context


class TestDiagnosticsAgent:
    @pytest.mark.asyncio
    async def test_local_mode_returns_result(self, shared_context):
        agent = DiagnosticsAgent()
        result = await agent.run(
            query="Pods crashing with OOM",
            shared_context=shared_context,
            correlation_id="test-003",
            client=None,
        )
        assert result.agent == AgentRole.DIAGNOSTICS
        assert "local_analysis" in result.tools_used
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_analyzes_log_data(self, shared_context):
        shared_context["log_data"] = (
            "2025-01-15T10:00:00Z ERROR Connection refused\n"
            "2025-01-15T10:00:01Z ERROR Connection refused\n"
            "2025-01-15T10:00:02Z INFO Retrying...\n"
            "2025-01-15T10:00:03Z FATAL Out of memory\n"
        )
        agent = DiagnosticsAgent()
        result = await agent.run(
            query="Service is down",
            shared_context=shared_context,
            correlation_id="test-004",
            client=None,
        )
        assert "Error indicators found" in result.content
        assert "diagnostics_findings" in shared_context

    @pytest.mark.asyncio
    async def test_uses_research_context(self, shared_context):
        shared_context["research_findings"] = "Known issue with connection pooling."
        agent = DiagnosticsAgent()
        result = await agent.run(
            query="Connection errors",
            shared_context=shared_context,
            correlation_id="test-005",
            client=None,
        )
        assert "Research" in result.content or "research" in result.content.lower()


class TestRemediationAgent:
    @pytest.mark.asyncio
    async def test_local_mode_returns_plan(self, shared_context):
        agent = RemediationAgent()
        result = await agent.run(
            query="Fix the payment gateway timeout",
            shared_context=shared_context,
            correlation_id="test-006",
            client=None,
        )
        assert result.agent == AgentRole.REMEDIATION
        assert "local_planner" in result.tools_used
        # Should contain actionable checklist items
        assert "[ ]" in result.content

    @pytest.mark.asyncio
    async def test_includes_pr_checklist(self, shared_context):
        agent = RemediationAgent()
        result = await agent.run(
            query="Fix the crash",
            shared_context=shared_context,
            correlation_id="test-007",
            client=None,
        )
        assert "PR Checklist" in result.content

    @pytest.mark.asyncio
    async def test_shares_plan_in_context(self, shared_context):
        agent = RemediationAgent()
        await agent.run(
            query="Remediate the outage",
            shared_context=shared_context,
            correlation_id="test-008",
            client=None,
        )
        assert "remediation_plan" in shared_context
