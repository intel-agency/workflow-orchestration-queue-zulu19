# Architecture Document: workflow-orchestration-queue

**Last Updated:** 2026-03-27

## Executive Summary

workflow-orchestration-queue represents a paradigm shift from **Interactive AI Coding** to **Headless Agentic Orchestration**. The system transforms standard project management artifacts (GitHub Issues) into "Execution Orders" that are autonomously fulfilled by specialized AI agents.

The architecture is designed to be **Self-Bootstrapping** — the initial deployment is seeded from a template repository, and once active, the system uses its own orchestration capabilities to build and refine its components.

---

## System Architecture Overview

### Four Pillars Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     workflow-orchestration-queue                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐               │
│  │   THE EAR     │    │  THE STATE    │    │  THE BRAIN    │               │
│  │   (Notifier)  │───▶│   (Queue)     │◀───│  (Sentinel)   │               │
│  │               │    │               │    │               │               │
│  │  FastAPI      │    │  GitHub       │    │  Async Python │               │
│  │  Webhook      │    │  Issues/      │    │  Polling      │               │
│  │  Receiver     │    │  Labels       │    │  Service      │               │
│  └───────────────┘    └───────────────┘    └───────┬───────┘               │
│                                                     │                       │
│                                                     ▼                       │
│                                             ┌───────────────┐               │
│                                             │  THE HANDS    │               │
│                                             │  (Worker)     │               │
│                                             │               │               │
│                                             │  DevContainer │               │
│                                             │  opencode CLI │               │
│                                             │  LLM Agent    │               │
│                                             └───────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. The Ear (Work Event Notifier)

**Technology:** Python 3.12, FastAPI, Pydantic

**Responsibilities:**
- **Secure Webhook Ingestion:** Receives GitHub events at `/webhooks/github`
- **Cryptographic Verification:** Validates X-Hub-Signature-256 HMAC
- **Intelligent Triage:** Parses issue bodies to detect intent (Plan/Bug/Feature)
- **Queue Initialization:** Applies `agent:queued` label for valid triggers

**Key File:** `src/notifier_service.py`

**Security Model:**
- Rejects requests with invalid/missing signatures (HTTP 401)
- Responds with 202 Accepted within GitHub's 10-second timeout
- Never processes unverified payloads

---

### 2. The State (Work Queue)

**Philosophy:** "Markdown as a Database"

**Implementation:** Distributed state via GitHub Issues, Labels, and Milestones

**State Machine:**

```
┌─────────────────┐
│ agent:queued    │  ◀── Task validated, awaiting Sentinel
└────────┬────────┘
         │ (claim + assign)
         ▼
┌─────────────────┐
│agent:in-progress│  ◀── Sentinel owns task, Worker executing
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌─────────────────┐
│agent:  │ │agent:           │
│success │ │error/infra-fail │
└────────┘ └─────────────────┘
```

**Concurrency Control:**
- Uses GitHub Assignees as distributed lock
- **Assign-then-verify pattern:** 
  1. Assign `SENTINEL_BOT_LOGIN` to issue
  2. Re-fetch issue
  3. Verify assignment before proceeding
- Prevents race conditions between multiple Sentinel instances

---

### 3. The Brain (Sentinel Orchestrator)

**Technology:** Python Async, HTTPX, PowerShell Core

**Responsibilities:**
- **Polling Discovery:** Queries GitHub API every 60 seconds for `agent:queued` issues
- **Auth Synchronization:** Runs `scripts/gh-auth.ps1` before execution
- **Shell-Bridge Protocol:** Manages Worker via `devcontainer-opencode.sh`
- **Telemetry:** Posts heartbeat comments every 5 minutes during long tasks
- **Graceful Shutdown:** Handles SIGTERM/SIGINT, finishes current task, exits cleanly

**Key File:** `src/orchestrator_sentinel.py`

**Shell-Bridge Commands:**
| Command | Purpose | Timeout |
|---------|---------|---------|
| `up` | Provision Docker network/volumes | 60-300s |
| `start` | Launch opencode-server in container | 60s |
| `prompt` | Execute workflow instruction | 5700s (95 min) |
| `stop` | Stop container (prevent state bleed) | 60s |

**Rate Limit Handling:**
- Jittered exponential backoff on HTTP 403/429
- Max backoff: 960s (16 min)
- Reset to `POLL_INTERVAL` on success

---

### 4. The Hands (Opencode Worker)

**Technology:** opencode CLI, LLM (GLM-5), DevContainers

**Environment:** High-fidelity DevContainer from template repository

**Capabilities:**
- **Contextual Awareness:** Accesses project structure via vector indexing
- **Instructional Logic:** Reads `.md` workflow modules from `local_ai_instruction_modules/`
- **Verification:** Runs local test suites before PR submission

**Key Principle:** Worker operates in identical environment to human developers

---

## Data Models

### WorkItem (Unified)

```python
class WorkItem(BaseModel):
    id: str                    # Issue number or unique ID
    source_url: str            # GitHub issue URL
    context_body: str          # Issue description
    target_repo_slug: str      # Owner/repo
    task_type: TaskType        # PLAN, IMPLEMENT, etc.
    status: WorkItemStatus     # QUEUED, IN_PROGRESS, etc.
    metadata: dict             # Provider-specific info (issue_node_id, etc.)
```

**Location:** `src/models/work_item.py`

### TaskType Enum

```python
class TaskType(Enum):
    PLAN = "plan"
    IMPLEMENT = "implement"
    BUGFIX = "bugfix"
    REVIEW = "review"
```

### WorkItemStatus Enum

```python
class WorkItemStatus(Enum):
    QUEUED = "agent:queued"
    IN_PROGRESS = "agent:in-progress"
    SUCCESS = "agent:success"
    ERROR = "agent:error"
    INFRA_FAILURE = "agent:infra-failure"
    STALLED_BUDGET = "agent:stalled-budget"
```

---

## Security Architecture

### Network Isolation

```
┌─────────────────────────────────────────────────────────────────┐
│                        HOST SERVER                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator                          │   │
│  │                  (Sentinel + Notifier)                   │   │
│  └───────────────────────────┬─────────────────────────────┘   │
│                              │                                  │
│              ┌───────────────┴───────────────┐                  │
│              ▼                               ▼                  │
│  ┌─────────────────────┐        ┌─────────────────────┐        │
│  │   Docker Network    │        │   Host Network      │        │
│  │   (Isolated)        │        │   (Protected)       │        │
│  │                     │        │                     │        │
│  │  ┌───────────────┐  │        │  ┌───────────────┐  │        │
│  │  │   Worker      │  │        │  │   Sentinel    │  │        │
│  │  │   Container   │  │        │  │   Service     │  │        │
│  │  └───────────────┘  │        │  └───────────────┘  │        │
│  │                     │        │                     │        │
│  │  ❌ No host access  │        │  ✅ GitHub API      │        │
│  │  ❌ No IMDS         │        │  ✅ Shell bridge    │        │
│  │  ✅ Internet OK     │        │                     │        │
│  └─────────────────────┘        └─────────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Credential Management

| Layer | Mechanism |
|-------|-----------|
| **Injection** | Temporary environment variables (in-memory only) |
| **Scoping** | GitHub App Installation Tokens (least privilege) |
| **Destruction** | Variables destroyed on container exit |
| **Scrubbing** | Regex patterns strip secrets from logs before GitHub posting |

### Secret Scrubbing Patterns

```python
PATTERNS = [
    r'ghp_[A-Za-z0-9_]+',        # GitHub PAT (personal)
    r'ghs_[A-Za-z0-9_]+',        # GitHub PAT (server)
    r'gho_[A-Za-z0-9_]+',        # GitHub PAT (OAuth)
    r'github_pat_[A-Za-z0-9_]+', # GitHub fine-grained PAT
    r'Bearer\s+[A-Za-z0-9_-]+',  # Bearer tokens
    r'sk-[A-Za-z0-9]+',          # OpenAI-style keys
    r'zhipu_[A-Za-z0-9]+',       # ZhipuAI keys
]
```

---

## Data Flow (Happy Path)

```
1. User opens GitHub Issue with [Plan] template
          │
          ▼
2. GitHub Webhook → Notifier (FastAPI)
          │
          ▼
3. Notifier validates signature, triages, applies agent:queued
          │
          ▼
4. Sentinel polls, discovers issue, claims via assign-then-verify
          │
          ▼
5. Sentinel runs devcontainer-opencode.sh up
          │
          ▼
6. Sentinel dispatches prompt with workflow instruction
          │
          ▼
7. Worker (opencode) executes, creates sub-issues, pushes branch
          │
          ▼
8. Sentinel detects exit code 0, applies agent:success
          │
          ▼
9. PR created, linked to original issue
```

---

## Architectural Decision Records (ADRs)

### ADR-07: Shell-Bridge Execution

**Decision:** Orchestrator interacts with Worker exclusively via `devcontainer-opencode.sh`

**Rationale:**
- Existing scripts handle complex Docker logic
- Prevents "Configuration Drift" between AI and human environments
- Python code stays lightweight (logic/state only)

**Consequence:** Clear separation between Logic Layer and Infrastructure Layer

---

### ADR-08: Polling-First Resiliency

**Decision:** Sentinel uses polling as primary discovery; webhooks are optimization

**Rationale:**
- Webhooks are "fire and forget" — events lost if server down
- Polling enables automatic state reconciliation on restart
- Self-healing against network partitions

---

### ADR-09: Provider-Agnostic Interface

**Decision:** All queue interactions abstracted behind `ITaskQueue` interface

**Rationale:**
- Enables future support for Linear, Notion, or internal queues
- Orchestrator logic unchanged when swapping providers
- Strategy Pattern for extensibility

---

## Self-Bootstrapping Lifecycle

```
Stage 0 (Seeding)
    │ Manual clone of template repository
    ▼
Stage 1 (Manual Launch)
    │ Run devcontainer-opencode.sh up
    ▼
Stage 2 (Project Setup)
    │ Run project-setup workflow
    │ Agent configures environment, indices
    ▼
Stage 3 (Handover)
    │ Start sentinel.py service
    │ Developer interacts only via GitHub Issues
    ▼
Stage 4 (Autonomous)
    └─ AI builds remaining features via self-orchestration
```

---

## Resource Constraints

| Resource | Limit | Rationale |
|----------|-------|-----------|
| Worker CPU | 2 cores | Prevent runaway agents |
| Worker RAM | 4 GB | DoS protection for host |
| Prompt Timeout | 95 min | Higher than inner watchdog (90 min) |
| Infrastructure Timeout | 60-300s | Container ops should be fast |

---

## Project Structure

```
workflow-orchestration-queue/
├── pyproject.toml               # uv dependencies and metadata
├── uv.lock                      # Deterministic lockfile
├── src/
│   ├── notifier_service.py      # FastAPI webhook receiver
│   ├── orchestrator_sentinel.py # Background polling service
│   ├── models/
│   │   ├── work_item.py         # WorkItem, TaskType, WorkItemStatus
│   │   └── github_events.py     # GitHub webhook payload schemas
│   └── queue/
│       └── github_queue.py      # ITaskQueue + GitHubQueue
├── scripts/
│   ├── devcontainer-opencode.sh # Shell bridge
│   ├── gh-auth.ps1              # GitHub auth utility
│   └── update-remote-indices.ps1
├── local_ai_instruction_modules/
│   ├── create-app-plan.md
│   ├── perform-task.md
│   └── analyze-bug.md
└── docs/
    └── [architecture, development guides]
```

---

## References

- **OS-APOW Architecture Guide v3.2** — Detailed component diagrams
- **OS-APOW Development Plan v4.2** — Phase breakdown and user stories
- **OS-APOW Implementation Specification v1.2** — Requirements and acceptance criteria
