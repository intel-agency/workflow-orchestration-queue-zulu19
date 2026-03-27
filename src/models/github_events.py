"""GitHub webhook event payload schemas.

This module defines Pydantic models for parsing and validating
GitHub webhook event payloads received by the notifier service.
"""

from typing import Any

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user information."""

    login: str
    id: int
    node_id: str | None = None
    avatar_url: str | None = None
    type: str | None = None


class GitHubRepository(BaseModel):
    """GitHub repository information."""

    id: int
    name: str
    full_name: str
    owner: GitHubUser
    private: bool = False
    html_url: str | None = None


class GitHubLabel(BaseModel):
    """GitHub label information."""

    id: int
    name: str
    color: str | None = None
    description: str | None = None


class GitHubIssue(BaseModel):
    """GitHub issue information."""

    id: int
    number: int
    title: str
    body: str | None = None
    state: str
    user: GitHubUser
    labels: list[GitHubLabel] = Field(default_factory=list)
    html_url: str | None = None
    node_id: str | None = None
    assignees: list[GitHubUser] = Field(default_factory=list)
    milestone: dict[str, Any] | None = None


class GitHubWebhookEvent(BaseModel):
    """Base GitHub webhook event payload.

    This is a generic structure that captures common fields
    across different GitHub webhook event types.
    """

    action: str | None = None
    issue: GitHubIssue | None = None
    repository: GitHubRepository
    sender: GitHubUser | None = None

    # For label events
    label: GitHubLabel | None = None

    # Raw event type (from X-GitHub-Event header)
    event_type: str | None = None

    model_config = {"extra": "allow"}


class IssuesEvent(GitHubWebhookEvent):
    """GitHub 'issues' webhook event."""

    action: str  # opened, edited, closed, reopened, labeled, unlabeled, etc.
    issue: GitHubIssue


class IssueCommentEvent(GitHubWebhookEvent):
    """GitHub 'issue_comment' webhook event."""

    action: str  # created, edited, deleted
    issue: GitHubIssue
    comment: dict[str, Any]  # Comment details


class PullRequestEvent(GitHubWebhookEvent):
    """GitHub 'pull_request' webhook event."""

    action: str  # opened, synchronize, closed, etc.
    pull_request: dict[str, Any]  # PR details


class PullRequestReviewEvent(GitHubWebhookEvent):
    """GitHub 'pull_request_review' webhook event."""

    action: str  # submitted, edited, dismissed
    pull_request: dict[str, Any]
    review: dict[str, Any]


class PullRequestReviewCommentEvent(GitHubWebhookEvent):
    """GitHub 'pull_request_review_comment' webhook event."""

    action: str  # created, edited, deleted
    pull_request: dict[str, Any]
    comment: dict[str, Any]
