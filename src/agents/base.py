# ---------------------------------------------------------------------------
# base.py — Base class for specialist agents
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.models import AgentResult, AgentRole

logger = logging.getLogger("incident-triage-copilot")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class BaseSpecialistAgent(ABC):
    """Abstract base for specialist agents in the triage pipeline.

    Each specialist:
    1. Has a role and system prompt loaded from disk.
    2. Receives the user query + shared context.
    3. Returns an ``AgentResult`` with its findings.
    """

    role: AgentRole
    prompt_file: str  # filename inside src/prompts/

    def __init__(self) -> None:
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        path = PROMPTS_DIR / self.prompt_file
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning("Prompt file %s not found — using fallback.", path)
        return f"You are the {self.role.value} specialist agent."

    @abstractmethod
    async def run(
        self,
        query: str,
        shared_context: dict,
        correlation_id: str,
        client: Optional[object] = None,
    ) -> AgentResult:
        """Execute the specialist's analysis and return results."""
        ...
