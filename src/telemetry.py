# ---------------------------------------------------------------------------
# telemetry.py — Observability setup (OpenTelemetry + Application Insights)
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import uuid
from typing import Optional

from src.config import AgentConfig

logger = logging.getLogger("incident-triage-copilot")


def setup_telemetry(config: AgentConfig) -> None:
    """Initialize logging and optional OpenTelemetry export."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )

    if config.app_insights_connection_string:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(
                connection_string=config.app_insights_connection_string
            )
            logger.info("Application Insights telemetry enabled.")
        except ImportError:
            logger.warning(
                "azure-monitor-opentelemetry not installed — "
                "Application Insights telemetry disabled."
            )
    else:
        logger.info("No APPLICATIONINSIGHTS_CONNECTION_STRING — telemetry to stdout only.")


def generate_correlation_id(existing: Optional[str] = None) -> str:
    """Return an existing correlation ID or create a new one.

    Every request/response pair carries a correlation ID so operators can
    trace a user query through the coordinator → specialist chain.
    """
    return existing or f"triage-{uuid.uuid4().hex[:12]}"
