# ---------------------------------------------------------------------------
# foundry_client.py — Microsoft Foundry client factory
# ---------------------------------------------------------------------------
# Creates an authenticated client for the Microsoft Foundry Agent Service.
#
# Authentication priority:
#   1. API key (PROJECT_API_KEY) — simplest for local dev
#   2. Managed Identity (AZURE_CLIENT_ID) — deployed environments
#   3. DefaultAzureCredential — az login, env creds, etc.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import Optional

from src.config import AgentConfig

logger = logging.getLogger("incident-triage-copilot")


async def create_foundry_client(config: AgentConfig) -> Optional[object]:
    """Create a Microsoft Foundry agent client if endpoint is configured.

    Returns None when running in local mode (no endpoint).
    """
    if config.is_local:
        logger.info("No Microsoft Foundry endpoint configured — running in local mode.")
        return None

    try:
        from azure.ai.agents.aio import AgentsClient

        # Auth priority: Managed Identity → DefaultAzureCredential (az login)
        # Note: AgentsClient requires AsyncTokenCredential (not AzureKeyCredential).
        if config.azure_client_id:
            from azure.identity.aio import ManagedIdentityCredential

            credential = ManagedIdentityCredential(
                client_id=config.azure_client_id
            )
            logger.info("Using Managed Identity credential (client_id=%s...)", config.azure_client_id[:8])
        else:
            from azure.identity.aio import DefaultAzureCredential

            credential = DefaultAzureCredential()
            logger.info("Using DefaultAzureCredential (local dev — az login).")

        client = AgentsClient(
            endpoint=config.ai_project_endpoint,
            credential=credential,
        )

        logger.info("Foundry AgentsClient created for endpoint: %s", config.ai_project_endpoint)
        return client

    except ImportError as exc:
        logger.error(
            "azure-ai-agents package not installed or import failed: %s. "
            "Run: pip install azure-ai-agents azure-identity",
            exc,
        )
        return None
    except Exception:
        logger.exception("Failed to create Foundry client.")
        return None
