# ---------------------------------------------------------------------------
# app.py — FastAPI server for the Incident Triage Copilot
# ---------------------------------------------------------------------------
# Provides the HTTP endpoints that azd ai agent invoke calls, and that
# Foundry Hosted Agents routes traffic to.
#
# Endpoints:
#   POST /responses  — Foundry Hosted Agent responses protocol (v1)
#   POST /triage     — Main triage endpoint (multi-agent pipeline)
#   GET  /health     — Health check for container orchestrator
#   GET  /readiness  — Readiness probe (Foundry Hosted Agents)
#   GET  /liveness   — Liveness probe (Foundry Hosted Agents)
#   GET  /           — Info page
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.agents.coordinator import Coordinator
from src.config import AgentConfig, load_config
from src.foundry_client import create_foundry_client
from src.models import HealthResponse, TriageRequest, TriageResponse
from src.telemetry import setup_telemetry

logger = logging.getLogger("incident-triage-copilot")

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    config = load_config()
    setup_telemetry(config)

    app = FastAPI(
        title="Incident Triage Copilot",
        description="Multi-agent incident triage powered by Microsoft Foundry",
        version="0.1.0",
    )

    # CORS — permissive for local dev, locked down in production via infra
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.is_local else [],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    # Static files for UI
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # State
    app.state.config = config
    app.state.coordinator = Coordinator()
    app.state.foundry_client = None  # initialized on startup

    @app.on_event("startup")
    async def _startup() -> None:
        app.state.foundry_client = await create_foundry_client(config)
        mode = "local" if config.is_local else "foundry"
        logger.info("Incident Triage Copilot started in %s mode.", mode)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        if app.state.foundry_client is not None:
            try:
                await app.state.foundry_client.close()
            except Exception:
                pass
        logger.info("Incident Triage Copilot shutting down.")

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @app.get("/", response_class=FileResponse)
    async def root():
        index = Path(__file__).parent / "static" / "index.html"
        if index.is_file():
            return FileResponse(str(index))
        return {
            "name": "Incident Triage Copilot",
            "version": "0.1.0",
            "mode": "local" if config.is_local else "foundry",
            "docs": "/docs",
        }

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            mode="local" if config.is_local else "foundry",
        )

    @app.get("/readiness", response_model=HealthResponse)
    async def readiness():
        """Readiness probe for Foundry Hosted Agents container orchestrator."""
        return HealthResponse(
            status="ready",
            version="0.1.0",
            mode="local" if config.is_local else "foundry",
        )

    @app.get("/liveness", response_model=HealthResponse)
    async def liveness():
        """Liveness probe for Foundry Hosted Agents container orchestrator."""
        return HealthResponse(
            status="alive",
            version="0.1.0",
            mode="local" if config.is_local else "foundry",
        )

    @app.post("/triage", response_model=TriageResponse)
    async def triage(request: TriageRequest):
        """Run the multi-agent triage pipeline.

        This is the endpoint that ``azd ai agent invoke`` calls.
        """
        try:
            response = await app.state.coordinator.triage(
                request=request,
                client=app.state.foundry_client,
                max_turns=config.max_turns,
            )
            return response
        except Exception as exc:
            logger.exception("Triage pipeline failed")
            detail = f"Triage pipeline failed: {exc}" if config.is_local else "Triage pipeline failed. Check logs for details."
            raise HTTPException(status_code=500, detail=detail)

    @app.post("/responses")
    async def responses(request: Request):
        """Foundry Hosted Agent responses protocol (v1).

        Accepts the OpenAI Responses API format and maps it to the
        internal triage pipeline, returning results in the expected format.
        """
        try:
            body = await request.json()
            req_headers = dict(request.headers)
            logger.info("Responses request headers: %s", {k: v for k, v in req_headers.items() if 'auth' not in k.lower()})
            logger.info("Responses request body keys: %s, id=%s, model=%s", list(body.keys()), body.get("id"), body.get("model"))

            # Extract user message from the responses API input
            user_message = ""
            input_items = body.get("input", [])
            if isinstance(input_items, str):
                user_message = input_items
            elif isinstance(input_items, list):
                for item in input_items:
                    if isinstance(item, str):
                        user_message = item
                        break
                    if isinstance(item, dict):
                        if item.get("role") == "user":
                            content = item.get("content", "")
                            if isinstance(content, str):
                                user_message = content
                            elif isinstance(content, list):
                                for part in content:
                                    if isinstance(part, dict) and part.get("type") == "input_text":
                                        user_message = part.get("text", "")
                                        break
                            break

            if not user_message:
                return JSONResponse(
                    status_code=400,
                    content={"error": {"message": "No user message found in input"}},
                )

            # Run the triage pipeline
            triage_request = TriageRequest(message=user_message)
            triage_response = await app.state.coordinator.triage(
                request=triage_request,
                client=app.state.foundry_client,
                max_turns=config.max_turns,
            )

            # Format as OpenAI Responses API output — must match the exact
            # schema the Foundry proxy validates against.
            # Echo back request fields + add our output.
            import time
            now = int(time.time())
            # Strip markdown formatting for Foundry compatibility
            summary_text = triage_response.summary.replace("`", "'").replace("**", "").replace("##", "").replace("---", "---")
            model = body.get("model", "gpt-4o")
            msg_id = f"msg_{uuid.uuid4().hex[:24]}"

            response_body = {
                "id": body.get("id", f"resp_{uuid.uuid4().hex[:24]}"),
                "object": "response",
                "created_at": now,
                "status": "completed",
                "error": None,
                "incomplete_details": None,
                "instructions": body.get("instructions", None),
                "max_output_tokens": body.get("max_output_tokens", None),
                "model": model,
                "input": body.get("input", []),
                "output": [
                    {
                        "id": msg_id,
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": summary_text,
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "parallel_tool_calls": body.get("parallel_tool_calls", True),
                "previous_response_id": body.get("previous_response_id", None),
                "reasoning": body.get("reasoning", None),
                "store": body.get("store", True),
                "temperature": body.get("temperature", 1.0),
                "text": body.get("text", {"format": {"type": "text"}}),
                "tool_choice": body.get("tool_choice", "auto"),
                "tools": body.get("tools", []),
                "top_p": body.get("top_p", 1.0),
                "truncation": body.get("truncation", "disabled"),
                "usage": {
                    "input_tokens": max(1, len(user_message) // 4),
                    "output_tokens": max(1, len(summary_text) // 4),
                    "total_tokens": max(2, (len(user_message) + len(summary_text)) // 4),
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
                "user": body.get("user", None),
                "metadata": body.get("metadata", {}),
            }
            logger.info("Responses endpoint returning: id=%s, status=%s", response_body["id"], response_body["status"])
            return JSONResponse(content=response_body)
        except Exception as exc:
            logger.exception("Responses endpoint failed")
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(exc) if config.is_local else "Triage pipeline failed"}},
            )

    return app


# ---------------------------------------------------------------------------
# Module-level app instance (used by uvicorn)
# ---------------------------------------------------------------------------
app = create_app()
