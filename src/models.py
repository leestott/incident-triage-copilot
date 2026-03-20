# ---------------------------------------------------------------------------
# models.py — Pydantic models for request/response contracts
# ---------------------------------------------------------------------------
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Identifies which specialist agent produced a result."""

    COORDINATOR = "coordinator"
    RESEARCH = "research"
    DIAGNOSTICS = "diagnostics"
    REMEDIATION = "remediation"


class TriageRequest(BaseModel):
    """Inbound request to the incident triage copilot."""

    message: str = Field(..., min_length=1, description="User's incident query")
    correlation_id: Optional[str] = Field(
        None, description="Optional correlation ID for tracing"
    )
    context: Optional[dict] = Field(
        None, description="Optional structured context (logs, metrics, etc.)"
    )


class AgentResult(BaseModel):
    """Output from a single specialist agent."""

    agent: AgentRole
    content: str
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Self-assessed confidence"
    )
    tools_used: list[str] = Field(default_factory=list)


class TriageResponse(BaseModel):
    """Full response from the multi-agent triage pipeline."""

    correlation_id: str
    summary: str = Field(..., description="Coordinator's synthesized answer")
    specialists_invoked: list[AgentRole] = Field(default_factory=list)
    results: list[AgentResult] = Field(default_factory=list)
    turn_count: int = Field(0, description="Number of agent-to-agent turns used")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.1.0"
    mode: str = "local"  # or "foundry"
