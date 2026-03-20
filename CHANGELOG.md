# Changelog

All notable changes to the Multi-Agent Incident Triage Copilot are documented here.

## [0.2.0] - 2026-03-20

### Added
- **Web UI**: Built-in responsive web interface at `/` with incident query input, example chips, agent pipeline visualisation, expandable results with confidence scores, and query history.
- **API key authentication**: `PROJECT_API_KEY` support via `AzureKeyCredential` for local dev without `az login`.
- **Environment variable alignment**: `PROJECT_ENDPOINT` and `PROJECT_API_KEY` match Microsoft Learn quickstart conventions, with `AZURE_AI_PROJECT_ENDPOINT` fallback for azd compatibility.
- **Three-tier auth priority**: API key → Managed Identity → DefaultAzureCredential.
- **Environment Variables reference**: Full table in README with all variables, defaults, and auth priority chain.
- **E2E test script**: `scripts/e2e_test.py` for live server validation (9 tests).
- **Screenshots**: 6 Playwright-captured screenshots in `screenshots/` folder.
- **Blog post**: `blog_post.md` aimed at inspiring AI developers to build hosted agent solutions.
- **Known Issues**: `KNOWN_ISSUES.md` tracking SDK compatibility, routing, and deployment issues.

### Changed
- **Renamed "Microsoft Foundry" branding**: Updated across all 16+ files (source, UI, prompts, infra, config, README).
- **Dockerfile**: Changed from hardcoded port 8080 to `PORT` env var via `python -m src`. Default port set to 8088 for Foundry Hosted Agent compatibility.
- **SDK API calls**: Updated from `client.agents.create_agent()` to `client.create_agent()` (and threads, messages, runs, delete) for azure-ai-agents v1.2.x compatibility.
- **BingGroundingTool**: Added graceful fallback when no `connection_id` is configured, preventing crashes in Foundry mode without Bing connection.
- **README deployment instructions**: Fixed all `azd ai agent` CLI commands to match actual v0.1.16-preview syntax:
  - `--from-manifest` → `--manifest`
  - `--message "text"` → `"text"` (positional argument)
  - `--remote` → removed (remote is default; use `--local` for local)
  - `--context` → removed (not a supported flag)
  - Added `az login` as first prerequisite step
  - Added Azure CLI as prerequisite
  - Updated `azd ai agent show` and `monitor` descriptions to match actual output
- **README badges**: Fixed broken CI badge markdown (missing closing parenthesis).
- **FastAPI root endpoint**: Now serves the web UI HTML instead of JSON.
- **Test for root endpoint**: Updated to handle both HTML (UI) and JSON responses.

### Fixed
- **`foundry_client.py`**: Import of `AzureKeyCredential` for key-based auth.
- **`research_agent.py`**: `BingGroundingTool()` no longer crashes without a connection_id.
- **`diagnostics_agent.py`**: SDK API call path corrected.
- **`remediation_agent.py`**: SDK API call path corrected, including `delete_agent`.
- **Dockerfile health check**: Now reads `PORT` env var dynamically instead of hardcoded 8080.

### Deployed
- **Hosted Agent v4**: Deployed to Microsoft Foundry as `incident-triage-copilot` (version 4).
  - Image: `oncallcopilotacr.azurecr.io/incident-triage-copilot:v4`
  - Container: 1 CPU, 2Gi memory, port 8088
  - Protocol: responses v1
  - Project: `leestott-9390-hosted`

---

## [0.1.0] - Initial Release

### Added
- Multi-agent incident triage pipeline with Coordinator, Research, Diagnostics, and Remediation agents.
- FastAPI server with `/triage`, `/health`, and `/` endpoints.
- Local mode with heuristic-based responses (no Azure required).
- Foundry mode with GPT-4o, Bing Grounding, and Code Interpreter.
- Shared context flow between agents (Research → Diagnostics → Remediation).
- Keyword-based routing with diagnostics and remediation keyword sets.
- Correlation IDs for end-to-end request tracing.
- Pydantic models for request/response validation.
- System prompts for each agent role in `src/prompts/`.
- Bicep infrastructure (Foundry Hub, Project, ACR, Container App, Managed Identity, App Insights).
- `agent.yaml` for Foundry Hosted Agent registration.
- `azure.yaml` for azd project configuration.
- Dockerfile with multi-stage build, non-root user, health check.
- Test suite: 39 tests across routing, agents, coordinator, API, and models.
- OpenTelemetry + Application Insights integration.
- Smoke test script for deployed endpoints.
