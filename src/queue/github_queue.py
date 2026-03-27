"""GitHub-based task queue implementation.

This module provides the ITaskQueue interface and its GitHub Issues-based
implementation for distributed work queue management.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from src.models.work_item import TaskType, WorkItem, WorkItemStatus

logger = logging.getLogger(__name__)


class ITaskQueue(ABC):
    """Abstract interface for task queue operations.

    This interface abstracts the underlying queue provider (GitHub Issues,
    Linear, Notion, etc.) to enable provider-agnostic orchestration logic.
    """

    @abstractmethod
    async def get_queued_items(self) -> list[WorkItem]:
        """Retrieve all items currently in the queue.

        Returns:
            List of WorkItem objects with QUEUED status.
        """
        pass

    @abstractmethod
    async def claim_item(self, item: WorkItem, assignee: str) -> bool:
        """Atomically claim a work item for processing.

        Uses assign-then-verify pattern to prevent race conditions.

        Args:
            item: The work item to claim.
            assignee: The identifier of the claiming agent.

        Returns:
            True if claim was successful, False if already claimed.
        """
        pass

    @abstractmethod
    async def update_status(
        self, item: WorkItem, status: WorkItemStatus, comment: str | None = None
    ) -> bool:
        """Update the status of a work item.

        Args:
            item: The work item to update.
            status: The new status.
            comment: Optional comment to add to the item.

        Returns:
            True if update was successful.
        """
        pass

    @abstractmethod
    async def add_comment(self, item: WorkItem, body: str) -> bool:
        """Add a comment to a work item.

        Args:
            item: The work item to comment on.
            body: The comment body.

        Returns:
            True if comment was added successfully.
        """
        pass


class GitHubQueue(ITaskQueue):
    """GitHub Issues-based task queue implementation.

    Uses GitHub Issues as the queue backend with labels for state management
    and assignees for distributed locking.

    State Machine:
        agent:queued -> agent:in-progress -> agent:success | agent:error | agent:infra-failure
    """

    def __init__(
        self,
        repo_slug: str,
        github_token: str,
        api_base_url: str = "https://api.github.com",
    ) -> None:
        """Initialize the GitHub queue.

        Args:
            repo_slug: Repository in 'owner/repo' format.
            github_token: GitHub API token with repo scope.
            api_base_url: GitHub API base URL (default: api.github.com).
        """
        self.repo_slug = repo_slug
        self.github_token = github_token
        self.api_base_url = api_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_queued_items(self) -> list[WorkItem]:
        """Query GitHub for issues with 'agent:queued' label.

        Returns:
            List of WorkItem objects representing queued issues.
        """
        url = f"{self.api_base_url}/repos/{self.repo_slug}/issues"
        params = {
            "state": "open",
            "labels": WorkItemStatus.QUEUED.value,
            "sort": "created",
            "direction": "asc",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            issues = response.json()

        work_items = []
        for issue in issues:
            task_type = self._detect_task_type(issue)
            work_items.append(
                WorkItem(
                    id=str(issue["number"]),
                    source_url=issue["html_url"],
                    context_body=issue.get("body", "") or "",
                    target_repo_slug=self.repo_slug,
                    task_type=task_type,
                    status=WorkItemStatus.QUEUED,
                    metadata={
                        "issue_node_id": issue.get("node_id"),
                        "title": issue.get("title"),
                    },
                )
            )

        logger.info(f"Found {len(work_items)} queued items")
        return work_items

    async def claim_item(self, item: WorkItem, assignee: str) -> bool:
        """Claim a work item using assign-then-verify pattern.

        Args:
            item: The work item to claim.
            assignee: GitHub username to assign.

        Returns:
            True if claim was successful.
        """
        issue_number = int(item.id)
        url = f"{self.api_base_url}/repos/{self.repo_slug}/issues/{issue_number}"

        async with httpx.AsyncClient() as client:
            # Step 1: Assign the issue
            assign_response = await client.patch(
                url,
                headers=self.headers,
                json={"assignees": [assignee]},
            )
            assign_response.raise_for_status()

            # Step 2: Re-fetch to verify assignment
            get_response = await client.get(url, headers=self.headers)
            get_response.raise_for_status()
            issue = get_response.json()

            # Step 3: Verify we're in the assignee list
            assignees = issue.get("assignees", [])
            if not any(a.get("login") == assignee for a in assignees):
                logger.warning(f"Failed to claim issue #{issue_number} - assignment not verified")
                return False

            # Step 4: Update label to in-progress
            await self._update_labels(client, issue_number, WorkItemStatus.IN_PROGRESS)

        logger.info(f"Successfully claimed issue #{issue_number}")
        return True

    async def update_status(
        self, item: WorkItem, status: WorkItemStatus, comment: str | None = None
    ) -> bool:
        """Update work item status by changing labels.

        Args:
            item: The work item to update.
            status: The new status.
            comment: Optional comment to add.

        Returns:
            True if successful.
        """
        issue_number = int(item.id)

        async with httpx.AsyncClient() as client:
            await self._update_labels(client, issue_number, status)

            if comment:
                await self._add_comment(client, issue_number, comment)

        logger.info(f"Updated issue #{issue_number} to {status.value}")
        return True

    async def add_comment(self, item: WorkItem, body: str) -> bool:
        """Add a comment to a work item.

        Args:
            item: The work item.
            body: Comment body.

        Returns:
            True if successful.
        """
        issue_number = int(item.id)

        async with httpx.AsyncClient() as client:
            await self._add_comment(client, issue_number, body)

        logger.info(f"Added comment to issue #{issue_number}")
        return True

    async def _update_labels(
        self, client: httpx.AsyncClient, issue_number: int, status: WorkItemStatus
    ) -> None:
        """Update issue labels to reflect new status."""
        url = f"{self.api_base_url}/repos/{self.repo_slug}/issues/{issue_number}/labels"

        # Get current labels
        get_response = await client.get(url, headers=self.headers)
        get_response.raise_for_status()
        current_labels = [label["name"] for label in get_response.json()]

        # Remove status labels and add new one
        status_prefix = "agent:"
        new_labels = [name for name in current_labels if not name.startswith(status_prefix)]
        new_labels.append(status.value)

        # Update labels
        put_response = await client.put(
            url,
            headers=self.headers,
            json={"labels": new_labels},
        )
        put_response.raise_for_status()

    async def _add_comment(self, client: httpx.AsyncClient, issue_number: int, body: str) -> None:
        """Add a comment to an issue."""
        url = f"{self.api_base_url}/repos/{self.repo_slug}/issues/{issue_number}/comments"

        response = await client.post(
            url,
            headers=self.headers,
            json={"body": body},
        )
        response.raise_for_status()

    def _detect_task_type(self, issue: dict[str, Any]) -> TaskType:
        """Detect task type from issue title/body."""
        title = issue.get("title", "").lower()
        body = issue.get("body", "") or ""
        body_lower = body.lower()

        if "[plan]" in title or "plan:" in title or "create a plan" in body_lower:
            return TaskType.PLAN
        if "bug" in title or "fix" in title or "bugfix" in body_lower:
            return TaskType.BUGFIX
        if "review" in title or "pr review" in body_lower:
            return TaskType.REVIEW

        return TaskType.IMPLEMENT
