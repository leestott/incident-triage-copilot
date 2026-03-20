# ---------------------------------------------------------------------------
# config.py — Centralized configuration for the agent runtime
# ---------------------------------------------------------------------------
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentConfig:
    """Configuration resolved from environment variables set by azd."""

    # Microsoft Foundry
    ai_project_endpoint: str = field(
        default_factory=lambda: os.environ.get(
            "PROJECT_ENDPOINT",
            os.environ.get("AZURE_AI_PROJECT_ENDPOINT", ""),
        )
    )
    model_deployment: str = field(
        default_factory=lambda: os.environ.get("MODEL_DEPLOYMENT", "gpt-4o")
    )

    # Authentication
    project_api_key: str = field(
        default_factory=lambda: os.environ.get("PROJECT_API_KEY", "")
    )
    azure_client_id: str = field(
        default_factory=lambda: os.environ.get("AZURE_CLIENT_ID", "")
    )

    # Observability
    app_insights_connection_string: str = field(
        default_factory=lambda: os.environ.get(
            "APPLICATIONINSIGHTS_CONNECTION_STRING", ""
        )
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO")
    )

    # Bing Grounding
    bing_connection_id: str = field(
        default_factory=lambda: os.environ.get("BING_CONNECTION_ID", "")
    )

    # Orchestration
    max_turns: int = field(
        default_factory=lambda: int(os.environ.get("MAX_AGENT_TURNS", "10"))
    )

    # Server
    host: str = field(
        default_factory=lambda: os.environ.get("HOST", "0.0.0.0")
    )
    port: int = field(
        default_factory=lambda: int(os.environ.get("PORT", "8080"))
    )

    @property
    def is_local(self) -> bool:
        """True when running locally (no Foundry endpoint configured)."""
        return not self.ai_project_endpoint


def load_config() -> AgentConfig:
    """Load configuration from environment / .env file."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    return AgentConfig()
