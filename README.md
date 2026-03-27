# workflow-orchestration-queue

[![Validate](https://github.com/intel-agency/workflow-orchestration-queue-zulu19/actions/workflows/validate.yml/badge.svg)](https://github.com/intel-agency/workflow-orchestration-queue-zulu19/actions/workflows/validate.yml)

A **headless agentic orchestration platform** that transforms GitHub Issues into autonomous execution orders. The system replaces interactive AI coding with a persistent background service that discovers work via polling, claims tasks using distributed locking, and dispatches AI workers via DevContainers.

## Overview

This project implements a "Four Pillars" architecture:

| Component | Name | Technology | Purpose |
|-----------|------|------------|---------|
| **The Ear** | Notifier | FastAPI | Webhook receiver for GitHub events |
| **The State** | Queue | GitHub Issues + Labels | Distributed state management |
| **The Brain** | Sentinel | Async Python | Background polling and orchestration |
| **The Hands** | Worker | opencode CLI + DevContainer | AI agent execution environment |

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for containerized deployment)

### Local Development

```bash
# Install dependencies
uv sync

# Run the notifier service
uv run uvicorn src.notifier_service:app --reload

# Run the sentinel service
uv run python -m src.orchestrator_sentinel

# Run tests
uv run pytest

# Run linting
uv run ruff check
```

### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Project Structure

```
workflow-orchestration-queue/
├── pyproject.toml           # uv dependencies and metadata
├── Dockerfile               # Container image
├── docker-compose.yml       # Local development orchestration
├── src/
│   ├── notifier_service.py  # FastAPI webhook receiver ("The Ear")
│   ├── orchestrator_sentinel.py # Background polling service ("The Brain")
│   ├── models/
│   │   ├── work_item.py     # WorkItem, TaskType, WorkItemStatus
│   │   └── github_events.py # GitHub webhook payload schemas
│   └── queue/
│       └── github_queue.py  # ITaskQueue + GitHubQueue implementation
├── tests/
│   └── test_notifier_service.py # Unit tests
├── scripts/
│   ├── devcontainer-opencode.sh # Shell bridge for worker execution
│   └── gh-auth.ps1          # GitHub authentication utility
├── docs/                    # Documentation
├── plan_docs/               # Architecture and planning documents
└── local_ai_instruction_modules/ # AI workflow instructions
```

## Architecture

The system uses a **polling-first** approach for resilience:

1. **Notifier** receives GitHub webhooks and applies `agent:queued` labels
2. **Sentinel** polls for queued issues every 60 seconds
3. **Sentinel** claims tasks using assign-then-verify pattern (distributed lock)
4. **Worker** executes in an isolated DevContainer via shell bridge
5. **Sentinel** updates issue status based on worker exit code

### State Machine

```
agent:queued → agent:in-progress → agent:success | agent:error | agent:infra-failure
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_WEBHOOK_SECRET` | Secret for webhook signature validation | - |
| `GITHUB_TOKEN` | GitHub API token for queue operations | - |
| `REPO_SLUG` | Target repository (owner/repo) | - |
| `SENTINEL_ID` | Unique instance identifier | sentinel-01 |
| `POLL_INTERVAL` | Seconds between polls | 60 |
| `LOG_LEVEL` | Logging level | INFO |

## API Documentation

When running the notifier service, access the OpenAPI documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_notifier_service.py -v
```

## Contributing

1. Create a feature branch
2. Make changes following the code style (enforced by Ruff)
3. Run tests and linting
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Additional Documentation

- [Repository Summary](.ai-repository-summary.md) - AI-friendly repository overview
- [Architecture Document](plan_docs/architecture.md) - Detailed system architecture
- [Tech Stack](plan_docs/tech-stack.md) - Technology decisions and rationale
