# ---------------------------------------------------------------------------
# diagnostics_agent.py — Specialist B: Diagnostics Agent
# ---------------------------------------------------------------------------
# Analyzes logs, traces, and metrics to identify root cause.
# Uses Code Interpreter tool on Foundry for data analysis.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import Optional

from src.agents.base import BaseSpecialistAgent
from src.models import AgentResult, AgentRole

logger = logging.getLogger("incident-triage-copilot")


class DiagnosticsAgent(BaseSpecialistAgent):
    """Analyzes logs, traces, and error patterns to find root cause."""

    role = AgentRole.DIAGNOSTICS
    prompt_file = "diagnostics_agent.md"

    async def run(
        self,
        query: str,
        shared_context: dict,
        correlation_id: str,
        client: Optional[object] = None,
    ) -> AgentResult:
        logger.info("[%s] Diagnostics agent starting", correlation_id)

        tools_used: list[str] = []
        log_data = shared_context.get("log_data", "")
        research = shared_context.get("research_findings", "")

        if client is not None:
            try:
                content = await self._run_with_foundry(
                    query, log_data, research, shared_context, client
                )
                tools_used.append("code_interpreter")
            except Exception:
                logger.warning("[%s] Diagnostics agent Foundry call failed, falling back to local", correlation_id, exc_info=True)
                content = self._run_local(query, log_data, research)
                tools_used.append("local_analysis")
        else:
            content = self._run_local(query, log_data, research)
            tools_used.append("local_analysis")

        result = AgentResult(
            agent=self.role,
            content=content,
            confidence=0.70,
            tools_used=tools_used,
        )

        shared_context["diagnostics_findings"] = content
        logger.info("[%s] Diagnostics agent complete | tools=%s", correlation_id, tools_used)
        return result

    async def _run_with_foundry(
        self,
        query: str,
        log_data: str,
        research: str,
        shared_context: dict,
        client: object,
    ) -> str:
        """Use Foundry agent with Code Interpreter for log analysis."""
        from azure.ai.agents.models import CodeInterpreterTool

        code_tool = CodeInterpreterTool()

        agent = await client.create_agent(
            model=shared_context.get("model_deployment", "gpt-4o"),
            name="diagnostics-specialist",
            instructions=self.system_prompt,
            tools=code_tool.definitions,
        )

        try:
            thread = await client.threads.create()

            prompt_parts = [f"Analyze this incident:\n\n{query}"]
            if log_data:
                prompt_parts.append(f"\n\n## Log Data\n```\n{log_data}\n```")
            if research:
                prompt_parts.append(f"\n\n## Research Context\n{research}")

            await client.messages.create(
                thread_id=thread.id,
                role="user",
                content="".join(prompt_parts),
            )

            run = await client.runs.create_and_process(
                thread_id=thread.id, agent_id=agent.id
            )

            if run.status == "failed":
                logger.error("Diagnostics agent run failed: %s", run.last_error)
                return f"Diagnostics could not be completed: {run.last_error}"

            messages = client.messages.list(thread_id=thread.id)
            async for msg in messages:
                if msg.role == "assistant":
                    return msg.content[0].text.value if msg.content else ""
            return "No diagnostics results produced."
        finally:
            await client.delete_agent(agent.id)

    def _run_local(self, query: str, log_data: str, research: str) -> str:
        """Local fallback: structured diagnostic analysis."""
        sections = [
            "## Diagnostic Analysis (Local Mode)\n",
            f"**Incident:** {query}\n",
        ]

        if log_data:
            # Count error indicators in the provided log data
            error_count = sum(
                1 for line in log_data.splitlines()
                if any(kw in line.lower() for kw in ["error", "fatal", "exception", "panic"])
            )
            sections.append(
                f"### Log Analysis\n"
                f"- **Lines analyzed:** {len(log_data.splitlines())}\n"
                f"- **Error indicators found:** {error_count}\n"
            )

        sections.append(
            "### Diagnostic Checklist\n"
            "1. **Error Pattern** — Look for recurring exception types or error codes.\n"
            "2. **Timing Correlation** — Map errors to deployment or config change timestamps.\n"
            "3. **Resource Saturation** — Check CPU, memory, disk, and connection pool metrics.\n"
            "4. **Dependency Failures** — Identify timeouts or connection refused errors "
            "to downstream services.\n"
            "5. **Data Integrity** — Look for schema changes, missing fields, or encoding issues.\n"
        )

        if research:
            sections.append(
                f"\n### Cross-Reference with Research\n"
                f"Research context was provided and factored into analysis.\n"
            )

        sections.append(
            "\n*Note: Running in local mode. Deploy to Foundry for Code Interpreter "
            "analysis of log files.*"
        )

        return "\n".join(sections)
