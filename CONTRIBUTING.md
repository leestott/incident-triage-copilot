# Contributing to Multi-Agent Incident Triage Copilot

Thank you for your interest in contributing! This guide will help you get set up for development.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/leestott/incident-triage-copilot.git
cd incident-triage-copilot

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install runtime + dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx ruff

# Copy environment template
cp .env.sample .env
```

## Running Locally

```bash
# Start the agent server (with hot-reload)
python -m src

# In another terminal, test it:
curl -X POST http://localhost:8080/triage \
  -H "Content-Type: application/json" \
  -d '{"message": "API returning 500 errors"}'
```

## Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_routing.py -v

# With coverage (install pytest-cov first)
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

## Linting

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/
```

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions.
- Use type hints for function signatures.
- Keep functions focused and under 50 lines where practical.
- Add docstrings for public classes and functions.
- Use the existing `logger` pattern for logging, always include the correlation ID.

## Adding a New Agent

1. Create `src/agents/new_agent.py` extending `BaseSpecialistAgent`.
2. Add the role to `AgentRole` enum in `src/models.py`.
3. Create `src/prompts/new_agent.md` with the system prompt.
4. Register in `Coordinator.__init__()` and update `_detect_specialists()`.
5. Add unit tests in `tests/test_agents.py`.
6. Add routing tests in `tests/test_routing.py`.

## Pull Request Guidelines

- Keep PRs focused: one feature or fix per PR.
- Include tests for new functionality.
- Ensure `ruff check` and `pytest` pass locally before pushing.
- Update the README if you change the agent design or add new features.

## Reporting Issues

Use GitHub Issues. Include:
- Steps to reproduce
- Expected vs. actual behaviour
- azd version (`azd version`)
- Python version (`python --version`)
- OS and version

## Code of Conduct

This project follows the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
