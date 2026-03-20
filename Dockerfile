# ---------------------------------------------------------------------------
# Dockerfile — Container image for the Incident Triage Copilot agent
# ---------------------------------------------------------------------------
# Multi-stage build: install dependencies, then copy app code.
# Runs as non-root user for security.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (cache-friendly layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Expose the agent endpoint port (configurable via PORT env var)
EXPOSE 8088

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8088\")}/health')"

# Start the agent — uses PORT env var from config.py
CMD ["python", "-m", "src"]
