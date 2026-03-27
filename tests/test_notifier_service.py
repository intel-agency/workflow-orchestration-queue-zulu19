"""Tests for the notifier service."""

import hashlib
import hmac
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.models.work_item import TaskType, WorkItem, WorkItemStatus
from src.notifier_service import (
    Settings,
    app,
    detect_intent,
    verify_webhook_signature,
)


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings."""
    return Settings(
        github_webhook_secret="test-secret",
        sentinel_bot_login="test-bot[bot]",
        log_level="DEBUG",
    )


class TestWebhookSignature:
    """Tests for webhook signature verification."""

    def test_valid_signature(self, mock_settings: Settings) -> None:
        """Test valid signature is accepted."""
        payload = b'{"test": "data"}'
        expected_sig = (
            "sha256="
            + hmac.new(
                mock_settings.github_webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
        )

        with patch("src.notifier_service.settings", mock_settings):
            result = verify_webhook_signature(payload, expected_sig)
            assert result is True

    def test_invalid_signature(self, mock_settings: Settings) -> None:
        """Test invalid signature is rejected."""
        payload = b'{"test": "data"}'
        invalid_sig = "sha256=invalid"

        with patch("src.notifier_service.settings", mock_settings):
            result = verify_webhook_signature(payload, invalid_sig)
            assert result is False

    def test_missing_signature(self, mock_settings: Settings) -> None:
        """Test missing signature is rejected."""
        payload = b'{"test": "data"}'

        with patch("src.notifier_service.settings", mock_settings):
            result = verify_webhook_signature(payload, None)
            assert result is False

    def test_no_secret_configured(self) -> None:
        """Test that no secret skips verification."""
        payload = b'{"test": "data"}'
        settings = Settings(github_webhook_secret="")

        with patch("src.notifier_service.settings", settings):
            result = verify_webhook_signature(payload, None)
            assert result is True


class TestIntentDetection:
    """Tests for intent detection."""

    def test_detect_plan_intent(self) -> None:
        """Test detection of plan intent."""
        event = {"action": "opened", "issue": {"title": "[Plan] New Feature"}}
        assert detect_intent(event) == "plan"

    def test_detect_bug_intent(self) -> None:
        """Test detection of bug intent."""
        event = {"action": "opened", "issue": {"title": "Bug: Something is broken"}}
        assert detect_intent(event) == "bugfix"

    def test_detect_feature_intent(self) -> None:
        """Test detection of feature intent."""
        event = {"action": "opened", "issue": {"title": "Feature: Add new thing"}}
        assert detect_intent(event) == "feature"

    def test_non_actionable_action(self) -> None:
        """Test non-actionable actions return None."""
        event = {"action": "closed", "issue": {"title": "[Plan] Something"}}
        assert detect_intent(event) is None


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health endpoint returns healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notifier"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root(self, client: TestClient) -> None:
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


class TestWorkItem:
    """Tests for WorkItem model."""

    def test_work_item_creation(self) -> None:
        """Test WorkItem can be created."""
        item = WorkItem(
            id="42",
            source_url="https://github.com/test/repo/issues/42",
            context_body="Test issue",
            target_repo_slug="test/repo",
            task_type=TaskType.IMPLEMENT,
        )
        assert item.id == "42"
        assert item.status == WorkItemStatus.QUEUED

    def test_work_item_with_metadata(self) -> None:
        """Test WorkItem with metadata."""
        item = WorkItem(
            id="42",
            source_url="https://github.com/test/repo/issues/42",
            context_body="Test issue",
            target_repo_slug="test/repo",
            task_type=TaskType.PLAN,
            metadata={"issue_node_id": "I_12345"},
        )
        assert item.metadata["issue_node_id"] == "I_12345"


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_types_exist(self) -> None:
        """Test all expected task types exist."""
        assert TaskType.PLAN.value == "plan"
        assert TaskType.IMPLEMENT.value == "implement"
        assert TaskType.BUGFIX.value == "bugfix"
        assert TaskType.REVIEW.value == "review"


class TestWorkItemStatus:
    """Tests for WorkItemStatus enum."""

    def test_status_values(self) -> None:
        """Test status values match expected labels."""
        assert WorkItemStatus.QUEUED.value == "agent:queued"
        assert WorkItemStatus.IN_PROGRESS.value == "agent:in-progress"
        assert WorkItemStatus.SUCCESS.value == "agent:success"
        assert WorkItemStatus.ERROR.value == "agent:error"
        assert WorkItemStatus.INFRA_FAILURE.value == "agent:infra-failure"
