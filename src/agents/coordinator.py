# ---------------------------------------------------------------------------
# coordinator.py — Coordinator Agent (Multi-Agent Orchestrator)
# ---------------------------------------------------------------------------
# The coordinator receives user queries, decides which specialist agents to
# invoke, manages shared context flow, and synthesizes the final response.
#
# Routing logic:
#   - All queries get Research (context is always useful)
#   - Queries with logs/errors/metrics → also Diagnostics
#   - Queries asking for fix/remediation/runbook → also Remediation
#   - If unsure, invoke all three (safe default)
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from src.agents.diagnostics_agent import DiagnosticsAgent
from src.agents.remediation_agent import RemediationAgent
from src.agents.research_agent import ResearchAgent
from src.models import AgentResult, AgentRole, TriageRequest, TriageResponse
from src.telemetry import generate_correlation_id

logger = logging.getLogger("incident-triage-copilot")

COORDINATOR_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "coordinator.md"
)

# Keywords that signal which specialists to invoke
_DIAGNOSTICS_KEYWORDS = {
    "log", "logs", "error", "exception", "stack trace", "traceback",
    "metric", "metrics", "latency", "timeout", "cpu", "memory", "oom",
    "crash", "panic", "500", "503", "429", "connection refused",
    "diagnose", "debug", "investigate", "analyze", "root cause",
}

_REMEDIATION_KEYWORDS = {
    "fix", "remediate", "remediation", "runbook", "checklist", "rollback",
    "hotfix", "patch", "resolve", "mitigate", "recover", "restore",
    "action plan", "next steps", "pr", "pull request", "deploy fix",
}


def _detect_specialists(query: str, context: Optional[dict]) -> list[AgentRole]:
    """Determine which specialist agents to invoke based on the query."""
    query_lower = query.lower()
    specialists: list[AgentRole] = []

    # Research is always invoked — context is universally useful
    specialists.append(AgentRole.RESEARCH)

    # Check for diagnostics signals
    has_diagnostics_signal = (
        any(kw in query_lower for kw in _DIAGNOSTICS_KEYWORDS)
        or (context and "log_data" in context)
    )
    if has_diagnostics_signal:
        specialists.append(AgentRole.DIAGNOSTICS)

    # Check for remediation signals (use word-boundary matching for short keywords)
    has_remediation_signal = any(
        re.search(r'\b' + re.escape(kw) + r'\b', query_lower) if len(kw) < 4
        else kw in query_lower
        for kw in _REMEDIATION_KEYWORDS
    )
    if has_remediation_signal:
        specialists.append(AgentRole.REMEDIATION)

    # If only research was selected and query is complex, add all
    if len(specialists) == 1 and len(query.split()) > 15:
        specialists.extend([AgentRole.DIAGNOSTICS, AgentRole.REMEDIATION])

    return specialists


class Coordinator:
    """Multi-agent coordinator that routes queries and synthesizes results."""

    def __init__(self) -> None:
        self.research_agent = ResearchAgent()
        self.diagnostics_agent = DiagnosticsAgent()
        self.remediation_agent = RemediationAgent()
        self.system_prompt = self._load_prompt()

        self._agent_map = {
            AgentRole.RESEARCH: self.research_agent,
            AgentRole.DIAGNOSTICS: self.diagnostics_agent,
            AgentRole.REMEDIATION: self.remediation_agent,
        }

    @staticmethod
    def _load_prompt() -> str:
        if COORDINATOR_PROMPT_PATH.exists():
            return COORDINATOR_PROMPT_PATH.read_text(encoding="utf-8")
        return "You are the coordinator of a multi-agent incident triage system."

    async def triage(
        self,
        request: TriageRequest,
        client: Optional[object] = None,
        max_turns: int = 10,
    ) -> TriageResponse:
        """Execute the multi-agent triage pipeline.

        Flow:
        1. Detect which specialists to invoke
        2. Build shared context
        3. Run specialists in sequence (each builds on prior context)
        4. Synthesize a unified response
        """
        correlation_id = generate_correlation_id(request.correlation_id)
        logger.info(
            "[%s] Coordinator starting triage | message=%s",
            correlation_id,
            request.message[:80],
        )

        # Step 1: Route to specialists
        specialists = _detect_specialists(request.message, request.context)
        logger.info(
            "[%s] Routing to specialists: %s",
            correlation_id,
            [s.value for s in specialists],
        )

        # Step 2: Shared context — all agents read/write to this dict
        from src.config import load_config
        _cfg = load_config()

        shared_context: dict = {
            "original_query": request.message,
            "model_deployment": _cfg.model_deployment,
        }
        if request.context:
            shared_context.update(request.context)

        # Inject Bing connection ID from app config (if not already in context)
        if "bing_connection_id" not in shared_context and _cfg.bing_connection_id:
            shared_context["bing_connection_id"] = _cfg.bing_connection_id

        # Step 3: Execute specialists sequentially (context flows forward)
        results: list[AgentResult] = []
        turn_count = 0

        for role in specialists:
            if turn_count >= max_turns:
                logger.warning("[%s] Max turns (%d) reached, stopping.", correlation_id, max_turns)
                break

            agent = self._agent_map[role]
            result = await agent.run(
                query=request.message,
                shared_context=shared_context,
                correlation_id=correlation_id,
                client=client,
            )
            results.append(result)
            turn_count += 1

        # Step 4: Synthesize
        summary = self._synthesize(request.message, results, correlation_id)

        response = TriageResponse(
            correlation_id=correlation_id,
            summary=summary,
            specialists_invoked=specialists,
            results=results,
            turn_count=turn_count,
        )

        logger.info(
            "[%s] Triage complete | specialists=%d turns=%d",
            correlation_id,
            len(specialists),
            turn_count,
        )
        return response

    @staticmethod
    def _synthesize(
        query: str, results: list[AgentResult], correlation_id: str
    ) -> str:
        """Combine specialist outputs into a coherent summary."""
        if not results:
            return "No specialist agents were invoked. Please provide more details about the incident."

        sections = [
            f"# Incident Triage Report\n",
            f"**Correlation ID:** `{correlation_id}`\n",
            f"**Query:** {query}\n",
            f"**Specialists consulted:** {', '.join(r.agent.value for r in results)}\n",
            "---\n",
        ]

        for result in results:
            sections.append(f"## {result.agent.value.title()} Agent\n")
            sections.append(f"{result.content}\n")
            if result.tools_used:
                sections.append(f"*Tools: {', '.join(result.tools_used)}*\n")
            sections.append("---\n")

        return "\n".join(sections)
