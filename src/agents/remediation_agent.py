# ---------------------------------------------------------------------------
# remediation_agent.py — Specialist C: Remediation Planner Agent
# ---------------------------------------------------------------------------
# Drafts runbooks, PR checklists, and remediation plans based on findings
# from the Research and Diagnostics agents.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import Optional

from src.agents.base import BaseSpecialistAgent
from src.models import AgentResult, AgentRole

logger = logging.getLogger("incident-triage-copilot")


class RemediationAgent(BaseSpecialistAgent):
    """Creates actionable remediation plans based on diagnostic findings."""

    role = AgentRole.REMEDIATION
    prompt_file = "remediation_agent.md"

    async def run(
        self,
        query: str,
        shared_context: dict,
        correlation_id: str,
        client: Optional[object] = None,
    ) -> AgentResult:
        logger.info("[%s] Remediation agent starting", correlation_id)

        tools_used: list[str] = []
        research = shared_context.get("research_findings", "")
        diagnostics = shared_context.get("diagnostics_findings", "")

        if client is not None:
            try:
                content = await self._run_with_foundry(
                    query, research, diagnostics, shared_context, client
                )
                tools_used.append("foundry_agent")
            except Exception:
                logger.warning("[%s] Remediation agent Foundry call failed, falling back to local", correlation_id, exc_info=True)
                content = self._run_local(query, research, diagnostics)
                tools_used.append("local_planner")
        else:
            content = self._run_local(query, research, diagnostics)
            tools_used.append("local_planner")

        result = AgentResult(
            agent=self.role,
            content=content,
            confidence=0.80,
            tools_used=tools_used,
        )

        shared_context["remediation_plan"] = content
        logger.info("[%s] Remediation agent complete | tools=%s", correlation_id, tools_used)
        return result

    async def _run_with_foundry(
        self,
        query: str,
        research: str,
        diagnostics: str,
        shared_context: dict,
        client: object,
    ) -> str:
        """Use Foundry agent to generate a detailed remediation plan."""
        agent = await client.create_agent(
            model=shared_context.get("model_deployment", "gpt-4o"),
            name="remediation-specialist",
            instructions=self.system_prompt,
        )

        try:
            thread = await client.threads.create()

            prompt_parts = [
                f"Create a remediation plan for this incident:\n\n{query}"
            ]
            if research:
                prompt_parts.append(f"\n\n## Research Findings\n{research}")
            if diagnostics:
                prompt_parts.append(f"\n\n## Diagnostic Findings\n{diagnostics}")

            await client.messages.create(
                thread_id=thread.id,
                role="user",
                content="".join(prompt_parts),
            )

            run = await client.runs.create_and_process(
                thread_id=thread.id, agent_id=agent.id
            )

            if run.status == "failed":
                logger.error("Remediation agent run failed: %s", run.last_error)
                return f"Remediation plan could not be generated: {run.last_error}"

            messages = client.messages.list(thread_id=thread.id)
            async for msg in messages:
                if msg.role == "assistant":
                    return msg.content[0].text.value if msg.content else ""
            return "No remediation plan generated."
        finally:
            await client.delete_agent(agent.id)

    def _run_local(self, query: str, research: str, diagnostics: str) -> str:
        """Local fallback: generate a structured remediation plan template."""
        plan = [
            "## Remediation Plan (Local Mode)\n",
            f"**Incident:** {query}\n",
            "### Immediate Actions (Next 30 minutes)\n"
            "- [ ] Acknowledge the incident in your status page / incident channel\n"
            "- [ ] Identify the blast radius — which users/services are affected?\n"
            "- [ ] If a recent deployment caused this, initiate rollback\n"
            "- [ ] Enable verbose logging on affected services\n",
            "### Short-Term Fix (Next 2-4 hours)\n"
            "- [ ] Apply targeted hotfix based on diagnostic findings\n"
            "- [ ] Verify fix in staging before promoting to production\n"
            "- [ ] Monitor error rates for 30 minutes post-fix\n"
            "- [ ] Update status page with resolution ETA\n",
            "### PR Checklist\n"
            "- [ ] Root cause addressed (not just symptoms)\n"
            "- [ ] Unit tests added for the failure scenario\n"
            "- [ ] Integration test covers the affected workflow\n"
            "- [ ] Monitoring alert added to catch recurrence\n"
            "- [ ] Runbook updated with lessons learned\n",
            "### Post-Incident\n"
            "- [ ] Schedule blameless post-mortem within 48 hours\n"
            "- [ ] Document timeline in incident tracker\n"
            "- [ ] Create follow-up tickets for systemic improvements\n"
            "- [ ] Review and update on-call escalation paths\n",
        ]

        if research:
            plan.append(
                "\n### Research Integration\n"
                "Research findings were incorporated into the plan above.\n"
            )
        if diagnostics:
            plan.append(
                "\n### Diagnostics Integration\n"
                "Diagnostic analysis was used to prioritize remediation steps.\n"
            )

        plan.append(
            "\n*Note: Running in local mode. Deploy to Foundry for AI-powered "
            "remediation planning.*"
        )

        return "\n".join(plan)
