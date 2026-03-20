# Known Issues

This document tracks known issues, limitations, and workarounds for the Multi-Agent Incident Triage Copilot.

---

## SDK Compatibility

### `BingGroundingTool` requires `connection_id` (azure-ai-agents >= 1.2.0)

**Impact:** Research agent fails in Foundry mode if no Bing connection is configured.

**Symptom:**
```
TypeError: BingGroundingTool.__init__() missing 1 required positional argument: 'connection_id'
```

**Workaround:** The research agent now gracefully falls back to running without Bing Grounding when no `connection_id` is available. To enable Bing Grounding, create a `BingLLMSearch` connection in your Foundry project and set the `BING_CONNECTION_ID` environment variable. The legacy `Bing.Search.v7` resource kind is deprecated: use the `AIServices` resource with a project connection instead. See the [Enable Bing Grounding](README.md#enable-bing-grounding-live-web-search) section in the README for full setup instructions.

**Status:** Mitigated in code. Full Bing Grounding requires a `BingLLMSearch` project connection. Config flows `BING_CONNECTION_ID` from environment → config → coordinator → research agent automatically.

---

### AgentsClient API surface changed in azure-ai-agents 1.2.x

**Impact:** The SDK methods moved from `client.agents.create_agent()` to `client.create_agent()` (and similarly for threads, messages, runs).

**Symptom:**
```
AttributeError: 'AgentsClient' object has no attribute 'agents'
```

**Fix applied:** All agent files updated to use the direct `client.create_agent()`, `client.threads.create()`, `client.messages.create()`, `client.runs.create_and_process()`, and `client.delete_agent()` methods.

**Status:** Fixed.

---

## Routing

### Foundry Hosted Agent `/responses` protocol persistence validation

**Impact:** When invoking the hosted agent via the Foundry API (`agent_invoke` / `azd ai agent invoke`), the Foundry proxy rejects the response with `"Response could not be saved due to invalid format"` even though the container returns a valid 200 OK response with correct JSON.

**Symptom:**
```json
{"error": {"code": "bad_request", "message": "Response could not be saved due to invalid format"}}
```

**Root cause:** The Foundry Hosted Agent `responses` protocol (preview) has strict validation at the persistence layer. The proxy validates the response against an internal schema before saving to the conversation store. The exact schema requirements are still being documented.

**Workaround:** Use the agent via the Web UI (`/triage` endpoint), direct HTTP POST to `/triage`, or `azd ai agent invoke --local`. These all work correctly. The Foundry portal invoke path requires the exact response persistence format.

**Status:** Known platform limitation. Container is healthy and `/triage` works end-to-end: only the Foundry `agent_invoke` persistence path is affected.

---

### Substring matching in remediation keywords

**Impact:** The keyword `"pr"` (intended for "pull request") matches substrings in words like "problems", "production", "provider", causing over-routing to the Remediation Agent.

**Symptom:** Queries containing words with "pr" as a substring trigger the Remediation Agent unexpectedly. The test `test_long_query_gets_all_specialists` fails because the routing selects Research + Remediation instead of only Research.

**Workaround:** Use word-boundary matching instead of substring matching for short keywords. A fix would replace `kw in query_lower` with a regex word-boundary check for keywords under 4 characters.

**Status:** Fixed. Short keywords (< 4 chars) now use word-boundary regex matching instead of substring matching.

---

## Provisioning

### `azd provision` fails with `invalid character '/' looking for beginning of value`

**Impact:** `azd provision` cannot parse `infra/main.parameters.json` and exits before any resources are created.

**Symptom:**
```
initializing provisioning manager: resolving bicep parameters file: error unmarshalling Bicep template parameters: invalid character '/' looking for beginning of value
```

**Root cause:** The `bingConnectionId` parameter in `infra/main.parameters.json` is set via `${BING_CONNECTION_ID}`. Azure AI Foundry connection IDs are ARM resource paths (e.g. `/subscriptions/.../connections/bing`). If `azd` fails to substitute the value within its surrounding quotes, the raw `/` is left as an unquoted JSON value, which is invalid and causes the Go JSON parser to fail.

**Workaround:** Ensure `BING_CONNECTION_ID` is set in your azd environment *before* provisioning:
```bash
azd env set BING_CONNECTION_ID "<your-connection-id>"
azd provision
```
If you do not need Bing Grounding, clear the variable so it resolves to an empty string:
```bash
azd env set BING_CONNECTION_ID ""
azd provision
```

**Status:** Known. Workaround available. A permanent fix would make `bingConnectionId` an optional parameter with a default of `""` in the Bicep template so an unset env var does not break JSON parsing.

---

## Deployment

### Hosted agent container activation delay

**Impact:** After starting a hosted agent container, the replica can take 2-5 minutes to transition from "Waiting" to "Running" state.

**Symptom:** Container status shows `state: "Activating"` with `container_state: "Waiting"` for several minutes after `agent_container_control` start.

**Workaround:** Wait 3-5 minutes after starting the container before invoking. Poll with `agent_container_status_get` until `replicas[0].state` is `"Running"`.

**Status:** Expected behaviour for container cold starts.

---

### Foundry Hosted Agent port must be 8088

**Impact:** Microsoft Foundry Hosted Agents expect the application to listen on port **8088** (not the common 8080). If the container listens on the wrong port, it will show `ActivationFailed` with `Unhealthy` health state.

**Symptom:**
```json
{"state": "ActivationFailed", "health_state": "Unhealthy"}
```

**Fix applied:** The Dockerfile now uses `python -m src` which reads the `PORT` environment variable from config. The hosted agent definition sets `PORT=8088`.

**Status:** Fixed.

---

### `az acr build` Unicode encoding error on Windows

**Impact:** ACR cloud build log streaming may fail on Windows with a `UnicodeEncodeError` due to emoji characters in build output.

**Symptom:**
```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 2828-2867
```

**Workaround:** Use `--no-logs` flag:
```bash
az acr build --registry <acr> --image <image>:<tag> --platform linux/amd64 --file Dockerfile . --no-logs
```

**Status:** Azure CLI issue. Using `--no-logs` avoids the problem.

---

## Local Development

### Multiple Python interpreters on Windows

**Impact:** On Windows with both system Python and a venv, commands may use the wrong interpreter, causing `ModuleNotFoundError` for project dependencies.

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Workaround:** Always activate the venv before running commands:
```bash
.venv\Scripts\activate
python -m src
```

**Status:** Windows environment behaviour. Not a bug.

---

### Port conflicts when restarting the server

**Impact:** If a previous server process is still running on port 8080, restarting fails with `[Errno 10048]`.

**Symptom:**
```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8080)
```

**Workaround:** Use a different port via the `PORT` environment variable, or close the existing terminal/process.

**Status:** Expected behaviour.

---

## Testing

### Pre-existing routing test failure

**Impact:** `tests/test_routing.py::TestRoutingLogic::test_long_query_gets_all_specialists` fails because the `"pr"` keyword substring match triggers remediation routing.

**Test output:**
```
FAILED - AssertionError: assert <AgentRole.DIAGNOSTICS: 'diagnostics'> in [<AgentRole.RESEARCH: 'research'>, <AgentRole.REMEDIATION: 'remediation'>]
```

**Root cause:** See "Substring matching in remediation keywords" above.

**Status:** Pre-existing. 38/39 tests pass.
