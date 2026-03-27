"""WorkItem model and related enums for the orchestration queue.

This module defines the core data structures for work items that flow
through the orchestration system.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(Enum):
    """Type of task to be executed by the worker."""

    PLAN = "plan"
    IMPLEMENT = "implement"
    BUGFIX = "bugfix"
    REVIEW = "review"


class WorkItemStatus(Enum):
    """Status of a work item in the queue.

    These map directly to GitHub labels used for state management.
    """

    QUEUED = "agent:queued"
    IN_PROGRESS = "agent:in-progress"
    SUCCESS = "agent:success"
    ERROR = "agent:error"
    INFRA_FAILURE = "agent:infra-failure"
    STALLED_BUDGET = "agent:stalled-budget"


class WorkItem(BaseModel):
    """Unified work item representation.

    This model abstracts the underlying task source (GitHub Issues, etc.)
    and provides a consistent interface for the orchestrator.
    """

    id: str = Field(..., description="Issue number or unique identifier")
    source_url: str = Field(..., description="GitHub issue URL")
    context_body: str = Field(..., description="Issue description/context")
    target_repo_slug: str = Field(..., description="Owner/repo (e.g., 'intel-agency/repo')")
    task_type: TaskType = Field(..., description="Type of task to execute")
    status: WorkItemStatus = Field(
        default=WorkItemStatus.QUEUED,
        description="Current status in the queue",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific info (issue_node_id, etc.)",
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "42",
                    "source_url": "https://github.com/intel-agency/repo/issues/42",
                    "context_body": "Implement user authentication",
                    "target_repo_slug": "intel-agency/repo",
                    "task_type": "implement",
                    "status": "agent:queued",
                    "metadata": {"issue_node_id": "I_12345"},
                }
            ]
        },
    }
