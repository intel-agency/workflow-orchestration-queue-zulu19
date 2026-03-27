# syntax=docker/dockerfile:1
# Dockerfile for workflow-orchestration-queue
# Python 3.12 with FastAPI for the notifier/sentinel services

FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Copy source code (must be after pyproject.toml for editable install)
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port for FastAPI
EXPOSE 8000

# Health check using Python stdlib (no curl required)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command: run the notifier service
CMD ["python", "-m", "uvicorn", "src.notifier_service:app", "--host", "0.0.0.0", "--port", "8000"]
