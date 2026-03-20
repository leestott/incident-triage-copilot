# ---------------------------------------------------------------------------
# research_agent.py — Specialist A: Research Agent
# ---------------------------------------------------------------------------
# Searches the web and knowledge bases for incident context using Foundry
# Bing Grounding tool when deployed, or local heuristics when running locally.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import Optional

from src.agents.base import BaseSpecialistAgent
from src.models import AgentResult, AgentRole

logger = logging.getLogger("incident-triage-copilot")


class ResearchAgent(BaseSpecialistAgent):
    """Searches for context about an incident using web search and knowledge bases."""

    role = AgentRole.RESEARCH
    prompt_file = "research_agent.md"

    async def run(
        self,
        query: str,
        shared_context: dict,
        correlation_id: str,
        client: Optional[object] = None,
    ) -> AgentResult:
        logger.info("[%s] Research agent starting | query=%s", correlation_id, query[:80])

        tools_used: list[str] = []

        if client is not None:
            # ── Foundry-hosted path: use Microsoft Foundry agent with Bing Grounding ──
            try:
                content = await self._run_with_foundry(query, shared_context, client)
                tools_used.append("bing_grounding")
            except Exception:
                logger.warning("[%s] Research agent Foundry call failed, falling back to local", correlation_id, exc_info=True)
                content = self._run_local(query, shared_context)
                tools_used.append("local_heuristic")
        else:
            # ── Local path: synthesize research from the query itself ──
            content = self._run_local(query, shared_context)
            tools_used.append("local_heuristic")

        result = AgentResult(
            agent=self.role,
            content=content,
            confidence=0.75,
            tools_used=tools_used,
        )

        # Share findings with downstream agents
        shared_context["research_findings"] = content
        logger.info("[%s] Research agent complete | tools=%s", correlation_id, tools_used)
        return result

    async def _run_with_foundry(
        self, query: str, shared_context: dict, client: object
    ) -> str:
        """Use the Microsoft Foundry agent SDK with Bing Grounding tool."""
        tools = []
        bing_enabled = False
        try:
            from azure.ai.agents.models import BingGroundingTool
            bing_connection = shared_context.get("bing_connection_id", "")
            if bing_connection:
                bing_tool = BingGroundingTool(connection_id=bing_connection)
                tools = bing_tool.definitions
                bing_enabled = True
        except Exception:
            pass  # Bing Grounding not available — proceed without it

        agent = await client.create_agent(
            model=shared_context.get("model_deployment", "gpt-4o"),
            name="research-specialist",
            instructions=self.system_prompt,
            tools=tools if tools else None,
        )

        try:
            thread = await client.threads.create()
            await client.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Research the following incident:\n\n{query}",
            )

            run = await client.runs.create_and_process(
                thread_id=thread.id, agent_id=agent.id
            )

            if run.status == "failed" and bing_enabled:
                # Bing Grounding failed — retry without it using plain Foundry LLM
                logger.warning("Research run failed with Bing Grounding, retrying without: %s", run.last_error)
                await client.delete_agent(agent.id)
                agent = await client.create_agent(
                    model=shared_context.get("model_deployment", "gpt-4o"),
                    name="research-specialist",
                    instructions=self.system_prompt,
                )
                thread = await client.threads.create()
                await client.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=f"Research the following incident:\n\n{query}",
                )
                run = await client.runs.create_and_process(
                    thread_id=thread.id, agent_id=agent.id
                )

            if run.status == "failed":
                logger.error("Research agent run failed: %s", run.last_error)
                return f"Research could not be completed: {run.last_error}"

            messages = client.messages.list(thread_id=thread.id)
            # Extract assistant's reply
            async for msg in messages:
                if msg.role == "assistant":
                    return msg.content[0].text.value if msg.content else ""
            return "No research results found."
        finally:
            await client.delete_agent(agent.id)

    def _run_local(self, query: str, shared_context: dict) -> str:
        """Local fallback: generate structured research guidance."""
        return (
            "## Research Findings (Local Mode)\n\n"
            f"**Incident Query:** {query}\n\n"
            "### Recommended Investigation Areas\n"
            "1. **Service Status Pages** — Check Azure Status, AWS Health, "
            "or relevant provider dashboards.\n"
            "2. **Recent Changes** — Review deployment logs from the last 24h "
            "for related services.\n"
            "3. **Known Issues** — Search internal knowledge base and Stack Overflow "
            "for similar error patterns.\n"
            "4. **Dependency Map** — Identify upstream/downstream services that "
            "may be affected.\n\n"
            "*Note: Running in local mode. Deploy to Foundry for live web search "
            "via Bing Grounding.*"
        )
