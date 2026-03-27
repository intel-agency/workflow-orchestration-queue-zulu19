# Technology Stack: workflow-orchestration-queue

**Last Updated:** 2026-03-27

## Overview

workflow-orchestration-queue is a headless agentic orchestration platform built on Python with modern async capabilities. The stack prioritizes performance, developer experience, and reproducibility through containerization.

---

## Languages & Runtimes

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Primary Language** | Python | 3.12+ | Core application logic, async orchestration |
| **Shell Scripts** | Bash / PowerShell Core | - | DevContainer bridge, auth utilities |

---

## Web Framework & Server

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Web Framework** | FastAPI | High-performance async webhook receiver ("The Ear") |
| **ASGI Server** | Uvicorn | Production server for FastAPI application |
| **Auto-docs** | Swagger/OpenAPI | Built-in API documentation at `/docs` |

---

## Data Validation & Settings

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Data Validation** | Pydantic | Strict schema validation for WorkItem, TaskType, WorkItemStatus |
| **Settings Management** | Pydantic Settings | Environment variable validation and loading |

---

## HTTP & API Communication

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Async HTTP Client** | HTTPX | Non-blocking GitHub REST API calls with connection pooling |
| **GitHub API** | GitHub REST API v3 | Issue management, label updates, PR operations |

---

## Package Management

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Package Manager** | uv | 0.10+ | Rust-based fast dependency resolution |
| **Lock File** | uv.lock | - | Deterministic package versions |
| **Config File** | pyproject.toml | - | Project metadata and dependencies |

---

## Containerization & Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containerization** | Docker | Worker isolation, reproducible environments |
| **Dev Environment** | DevContainers | Consistent development environment |
| **Orchestration** | Docker Compose | Multi-container scenarios (e.g., app + database) |

---

## LLM & AI Integration

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Agent Runtime** | opencode CLI | AI agent execution framework |
| **LLM Provider** | ZhipuAI GLM-5 | Primary model for agent reasoning |
| **Instruction Format** | Markdown modules | Decoupled prompt logic in `local_ai_instruction_modules/` |

---

## Security & Authentication

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Webhook Security** | HMAC SHA256 | X-Hub-Signature-256 validation |
| **GitHub Auth** | GitHub App Installation Tokens | Scoped API access |
| **Credential Management** | Environment Variables | Ephemeral, in-memory injection |
| **Secret Scrubbing** | Regex-based utility | Pattern stripping for logs (ghp_*, sk-*, etc.) |

---

## Logging & Observability

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Service Logging** | Python logging (StreamHandler) | Console output, container capture |
| **Worker Logs** | JSONL files | Persistent audit trail |
| **Public Telemetry** | GitHub Issue comments | Heartbeat updates, sanitized output |
| **Instance ID** | SENTINEL_ID | Unique instance tracking |

---

## Testing

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Test Framework** | pytest | Unit and integration tests |
| **Test Runner** | uv run pytest | Integrated test execution |
| **Coverage** | pytest-cov | Code coverage reporting |

---

## Code Quality

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Linter** | Ruff | Fast Python linting |
| **Type Checking** | mypy (optional) | Static type analysis |
| **Docstrings** | Google/Sphinx format | API documentation |

---

## External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| fastapi | ^0.115 | Web framework |
| uvicorn | ^0.34 | ASGI server |
| httpx | ^0.28 | Async HTTP client |
| pydantic | ^2.10 | Data validation |
| pydantic-settings | ^2.6 | Settings management |

---

## Development Tools

| Tool | Purpose |
|------|---------|
| `scripts/devcontainer-opencode.sh` | Shell bridge for worker execution |
| `scripts/gh-auth.ps1` | GitHub authentication utility |
| `scripts/common-auth.ps1` | Shared auth initialization |
| `scripts/update-remote-indices.ps1` | Vector index synchronization |

---

## Rationale

### Why Python 3.12+?
- Native async/await improvements
- Better error messages for debugging
- Performance optimizations over 3.11

### Why FastAPI?
- Built-in OpenAPI documentation
- Native Pydantic integration
- High-performance async handling
- Type hints throughout

### Why uv over pip/poetry?
- Orders of magnitude faster dependency resolution
- Rust-based reliability
- Modern lockfile format
- Drop-in replacement for pip

### Why HTTPX over requests?
- Full async support for non-blocking API calls
- Connection pooling for efficiency
- HTTP/2 support
- Modern API design

### Why DevContainers?
- Bit-for-bit identical environments
- Reproducible builds
- Integrated with GitHub Codespaces
- Security isolation for AI-generated code
