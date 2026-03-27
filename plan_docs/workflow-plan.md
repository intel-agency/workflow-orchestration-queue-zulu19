# Workflow Execution Plan: project-setup

**Generated:** 2026-03-27
**Workflow File:** `ai_instruction_modules/ai-workflow-assignments/dynamic-workflows/project-setup.md`
**Repository:** intel-agency/workflow-orchestration-queue-zulu19

---

## 1. Overview

### Workflow Name
**project-setup**

### Project Description
**workflow-orchestration-queue** is a headless agentic orchestration platform that transforms GitHub Issues into autonomous execution orders. It replaces interactive AI coding with a persistent background service that discovers work via polling, claims tasks using distributed locking, and dispatches AI workers via a shell-bridge to DevContainers.

### Total Assignments
- **Main Assignments:** 6
- **Pre-script Events:** 1 (create-workflow-plan)
- **Post-assignment Events:** 2 per assignment (validate-assignment-completion, report-progress)
- **Post-script Event:** 1 (apply orchestration:plan-approved label)

### High-Level Summary
This workflow initializes a fresh repository cloned from the workflow-orchestration-queue-zulu19 template, configures GitHub Project/labels, creates an application plan from seeded documents, scaffolds the Python project structure, adds AGENTS.md for AI context, documents learnings, and merges the setup PR.

---

## 2. Project Context Summary

### Key Facts from plan_docs/

| Category | Details |
|----------|---------|
| **Project Name** | workflow-orchestration-queue |
| **Repository** | intel-agency/workflow-orchestration-queue-zulu19 |
| **Purpose** | Headless agentic orchestration - transforms GitHub Issues into autonomous AI worker dispatches |
| **Primary Language** | Python 3.12+ |
| **Web Framework** | FastAPI (for webhook receiver/notifier) |
| **Package Manager** | uv (Rust-based, fast dependency resolution) |
| **Data Validation** | Pydantic |
| **HTTP Client** | HTTPX (async) |
| **Containerization** | Docker / DevContainers |
| **Shell Bridge** | `scripts/devcontainer-opencode.sh` |

### Architecture Overview (4 Pillars)
1. **The Ear (Notifier)** - FastAPI webhook receiver for GitHub events
2. **The State (Queue)** - GitHub Issues as database (labels: agent:queued, agent:in-progress, etc.)
3. **The Brain (Sentinel)** - Background polling service with distributed locking
4. **The Hands (Worker)** - DevContainer-based AI agent execution

### Key Constraints
- All GitHub Actions must be pinned to full commit SHA (no @v3 tags)
- Branch naming: `dynamic-workflow-project-setup`
- PR self-approval acceptable for setup workflow
- CI remediation loop: max 3 fix attempts before escalation
- Credential scrubbing required before posting logs to GitHub

### Known Risks from Plan Review
- Long-running subagent delegations (15+ min) need heartbeat
- Race conditions in task claiming need assign-then-verify pattern
- No cost guardrails yet (deferred to future phase)

---

## 3. Assignment Execution Plan

### Pre-script Event: create-workflow-plan

| Field | Content |
|-------|---------|
| **Assignment** | `create-workflow-plan`: Create Workflow Plan |
| **Goal** | Create comprehensive workflow execution plan before any assignments execute |
| **Key Acceptance Criteria** | • Dynamic workflow read and understood<br>• All assignments traced and read<br>• All plan_docs/ files read<br>• Plan presented and approved by stakeholder<br>• Committed to plan_docs/workflow-plan.md |
| **Project-Specific Notes** | This is a Python/FastAPI project with DevContainer execution. Plan docs include architecture guide, development plan, implementation spec, simplification report, and plan review. |
| **Prerequisites** | Dynamic workflow file accessible, plan_docs/ directory exists |
| **Dependencies** | None (first step) |
| **Risks / Challenges** | • plan_docs/ contains 5+ documents requiring synthesis<br>• Must fetch remote assignments from nam20485/agent-instructions |
| **Events** | None |

---

### Assignment 1: init-existing-repository

| Field | Content |
|-------|---------|
| **Assignment** | `init-existing-repository`: Initiate Existing Repository |
| **Goal** | Initialize repository with branch, labels, project, and initial PR |
| **Key Acceptance Criteria** | • New branch created (dynamic-workflow-project-setup)<br>• Branch protection ruleset imported<br>• GitHub Project created and linked<br>• Labels imported from .github/.labels.json<br>• Workspace/devcontainer files renamed<br>• PR created to main |
| **Project-Specific Notes** | • Uses scripts/import-labels.ps1 for labels<br>• Branch protection ruleset in .github/protected-branches_ruleset.json<br>• Requires GH_ORCHESTRATION_AGENT_TOKEN with administration:write scope |
| **Prerequisites** | GitHub auth with repo, project, read:project scopes |
| **Dependencies** | None (first main assignment) |
| **Risks / Challenges** | • Branch protection import requires PAT with admin scope<br>• PR creation requires at least one commit first |
| **Events** | post-assignment-complete: validate-assignment-completion, report-progress |

---

### Assignment 2: create-app-plan

| Field | Content |
|-------|---------|
| **Assignment** | `create-app-plan`: Create Application Plan |
| **Goal** | Create detailed application plan issue from plan_docs templates |
| **Key Acceptance Criteria** | • Application template analyzed<br>• Plan documented in GitHub Issue using template<br>• tech-stack.md and architecture.md created in plan_docs/<br>• Milestones created and linked<br>• Issue added to GitHub Project<br>• Labels applied (planning, documentation) |
| **Project-Specific Notes** | • Primary spec: OS-APOW Implementation Specification v1.2.md<br>• Tech stack: Python 3.12+, FastAPI, uv, Pydantic, HTTPX<br>• Architecture already documented in OS-APOW Architecture Guide v3.2.md |
| **Prerequisites** | init-existing-repository complete, plan_docs/ accessible |
| **Dependencies** | PR from assignment 1, project structure |
| **Risks / Challenges** | • Plan docs are extensive (5 files) - synthesis required<br>• Pre-assignment event: gather-context<br>• On-failure event: recover-from-error |
| **Events** | pre-assignment-begin: gather-context<br>on-assignment-failure: recover-from-error<br>post-assignment-complete: report-progress |

---

### Assignment 3: create-project-structure

| Field | Content |
|-------|---------|
| **Assignment** | `create-project-structure`: Create Project Structure |
| **Goal** | Create actual project scaffolding and infrastructure foundation |
| **Key Acceptance Criteria** | • Solution/project structure created<br>• All project files and directories established<br>• Docker/Docker Compose configured<br>• Documentation structure created<br>• CI/CD foundation established<br>• Repository summary (.ai-repository-summary.md) created<br>• All GitHub Actions SHA-pinned |
| **Project-Specific Notes** | • Python project with pyproject.toml (uv)<br>• Expected structure: src/notifier_service.py, src/orchestrator_sentinel.py, src/models/, src/queue/<br>• Dockerfile and docker-compose.yml required<br>• CI/CD: .github/workflows/ |
| **Prerequisites** | Application plan approved |
| **Dependencies** | Application plan issue, tech-stack.md |
| **Risks / Challenges** | • Must adapt to Python/uv stack (not .NET)<br>• Healthcheck must use Python stdlib (no curl)<br>• All workflow actions must be SHA-pinned |
| **Events** | post-assignment-complete: validate-assignment-completion, report-progress |

---

### Assignment 4: create-agents-md-file

| Field | Content |
|-------|---------|
| **Assignment** | `create-agents-md-file`: Create AGENTS.md File |
| **Goal** | Create AGENTS.md at repository root for AI agent context |
| **Key Acceptance Criteria** | • AGENTS.md exists at repository root<br>• Project overview, setup commands documented<br>• Build/test commands validated<br>• Code style conventions documented<br>• Project structure documented<br>• Commands validated by running them<br>• Committed and pushed |
| **Project-Specific Notes** | • Tech stack: Python 3.12+, FastAPI, uv, Pydantic<br>• Build: uv sync, uv run<br>• Test: uv run pytest<br>• Lint: uv run ruff check<br>• Cross-reference with README.md and .ai-repository-summary.md |
| **Prerequisites** | Project structure created, build/test tooling in place |
| **Dependencies** | create-project-structure outputs |
| **Risks / Challenges** | • Commands must be validated by running them<br>• Must not duplicate README.md content |
| **Events** | post-assignment-complete: validate-assignment-completion, report-progress |

---

### Assignment 5: debrief-and-document

| Field | Content |
|-------|---------|
| **Assignment** | `debrief-and-document`: Debrief and Document Learnings |
| **Goal** | Create comprehensive debrief report with lessons learned |
| **Key Acceptance Criteria** | • Detailed report created using template<br>• Report in .md format<br>• All 12 sections complete<br>• All deviations documented<br>• Stakeholder approval obtained<br>• Execution trace saved (debrief-and-document/trace.md) |
| **Project-Specific Notes** | • Report should capture Python/FastAPI specific learnings<br>• Document any issues with uv, DevContainer, GitHub auth |
| **Prerequisites** | All main assignments complete |
| **Dependencies** | All prior assignment outputs |
| **Risks / Challenges** | • Must capture all deviations from assignments<br>• Action items must be filed as GitHub issues |
| **Events** | post-assignment-complete: validate-assignment-completion, report-progress |

---

### Assignment 6: pr-approval-and-merge

| Field | Content |
|-------|---------|
| **Assignment** | `pr-approval-and-merge`: Pull Request Approval and Merge |
| **Goal** | Complete PR approval, resolve comments, merge, and close issues |
| **Key Acceptance Criteria** | • All CI checks pass (with up to 3 remediation attempts)<br>• Code review delegated (not self-review)<br>• PR review comments resolved via ai-pr-comment-protocol.md<br>• GraphQL verification artifacts captured<br>• Merge performed<br>• Source branch deleted<br>• Related issues closed |
| **Project-Specific Notes** | • PR number from init-existing-repository output<br>• Self-approval acceptable for setup workflow<br>• CI remediation loop mandatory (max 3 attempts) |
| **Prerequisites** | PR created, all assignments complete |
| **Dependencies** | PR number (#initiate-new-repository.init-existing-repository) |
| **Risks / Challenges** | • Long-running CI may need attention<br>• Must follow ai-pr-comment-protocol.md exactly |
| **Events** | post-assignment-complete: validate-assignment-completion, report-progress |

---

### Post-script Event: Apply orchestration:plan-approved

| Field | Content |
|-------|---------|
| **Event** | `post-script-complete`: Apply plan-approved label |
| **Goal** | Signal that the application plan is ready for epic creation |
| **Key Acceptance Criteria** | • Locate application plan issue from create-app-plan<br>• Apply label `orchestration:plan-approved`<br>• Record output |
| **Project-Specific Notes** | This label triggers the next phase of orchestration pipeline |
| **Prerequisites** | All assignments complete, PR merged |
| **Dependencies** | Application plan issue number |
| **Risks / Challenges** | None - straightforward label application |
| **Events** | None |

---

## 4. Sequencing Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROJECT-SETUP WORKFLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

[START]
    │
    ▼
┌─────────────────────────────────┐
│  pre-script-begin               │
│  ┌───────────────────────────┐  │
│  │ create-workflow-plan      │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Assignment 1                   │
│  ┌───────────────────────────┐  │
│  │ init-existing-repository  │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ validate-assignment       │  │
│  │ report-progress           │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Assignment 2                   │
│  ┌───────────────────────────┐  │
│  │ gather-context (event)    │  │
│  │ create-app-plan           │  │
│  │ report-progress           │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Assignment 3                   │
│  ┌───────────────────────────┐  │
│  │ create-project-structure  │  │
│  │ validate-assignment       │  │
│  │ report-progress           │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Assignment 4                   │
│  ┌───────────────────────────┐  │
│  │ create-agents-md-file     │  │
│  │ validate-assignment       │  │
│  │ report-progress           │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Assignment 5                   │
│  ┌───────────────────────────┐  │
│  │ debrief-and-document      │  │
│  │ validate-assignment       │  │
│  │ report-progress           │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Assignment 6                   │
│  ┌───────────────────────────┐  │
│  │ pr-approval-and-merge     │  │
│  │ validate-assignment       │  │
│  │ report-progress           │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  post-script-complete           │
│  ┌───────────────────────────┐  │
│  │ Apply plan-approved label │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    │
    ▼
[END]
```

---

## 5. Open Questions

| # | Question | Context | Resolution Needed Before |
|---|----------|---------|--------------------------|
| 1 | Is `GH_ORCHESTRATION_AGENT_TOKEN` already configured? | Required for branch protection ruleset import with `administration:write` scope | init-existing-repository |
| 2 | Should Phase 2 (Webhook) and Phase 3 (Deep Orchestration) features be included in initial plan? | Plan docs mention these as future phases - clarify scope | create-app-plan |
| 3 | Are there existing GitHub Projects in the org that should be used? | Assignment creates new project - confirm this is desired | init-existing-repository |
| 4 | What is the target Python version for pyproject.toml? | Plan docs specify 3.12+ - confirm exact version | create-project-structure |
| 5 | Should the Sentinel and Notifier be separate services or combined? | Architecture shows them as separate - confirm deployment model | create-project-structure |

---

## 6. Approval

**Plan Status:** ⏳ Pending Approval

**Stakeholder Review Required:** Yes

This workflow execution plan has been prepared and is ready for stakeholder review. Please review the plan and indicate:
- ✅ **Approved** - Proceed with workflow execution
- 🔄 **Changes Requested** - Specify modifications needed
- ❓ **Questions** - Address open questions before proceeding

---

*Document prepared by: Planner Agent*
*Date: 2026-03-27*
