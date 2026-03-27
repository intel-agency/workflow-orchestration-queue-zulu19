"""FastAPI webhook receiver service - "The Ear".

This service receives GitHub webhook events, validates their signatures,
triages them by intent, and initializes queue items for processing.
"""

import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    github_webhook_secret: str = ""
    sentinel_bot_login: str = "sentinel-bot[bot]"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler."""
    logger.info("Notifier service starting up")
    yield
    logger.info("Notifier service shutting down")


app = FastAPI(
    title="workflow-orchestration-queue Notifier",
    description="Webhook receiver for GitHub events - The Ear",
    version="0.1.0",
    lifespan=lifespan,
)


class WebhookResponse(BaseModel):
    """Response model for webhook endpoint."""

    status: str
    message: str


def verify_webhook_signature(payload: bytes, signature: str | None) -> bool:
    """Verify GitHub webhook HMAC signature.

    Args:
        payload: Raw request body bytes.
        signature: X-Hub-Signature-256 header value.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not settings.github_webhook_secret:
        logger.warning("No webhook secret configured - skipping signature verification")
        return True

    if not signature or not signature.startswith("sha256="):
        logger.warning("Invalid or missing signature format")
        return False

    expected_sig = signature.removeprefix("sha256=")
    computed_sig = hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig, computed_sig)


def detect_intent(event: dict[str, Any]) -> str | None:
    """Detect the intent of a GitHub event.

    Analyzes the event payload to determine if it represents
    a Plan, Bug, Feature, or other actionable request.

    Args:
        event: Parsed webhook event payload.

    Returns:
        Detected intent string or None if not actionable.
    """
    action = event.get("action")
    issue = event.get("issue", {})
    title = issue.get("title", "").lower()
    body = issue.get("body", "") or ""

    # Only process certain actions
    if action not in ("opened", "edited", "labeled", "reopened"):
        return None

    # Check for plan requests
    if "[plan]" in title or "create a plan" in body.lower():
        return "plan"

    # Check for bug reports
    if "bug" in title or "fix" in title:
        return "bugfix"

    # Check for feature requests
    if "feature" in title or "implement" in title:
        return "feature"

    # Default to implementation
    return "implement"


@app.post("/webhooks/github", response_model=WebhookResponse)
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
) -> WebhookResponse:
    """Handle incoming GitHub webhook events.

    Validates signature, parses event, detects intent, and
    applies appropriate labels for queue processing.

    Returns:
        WebhookResponse with status and message.
    """
    # Read raw body for signature verification
    payload = await request.body()

    # Verify signature
    if not verify_webhook_signature(payload, x_hub_signature_256):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON payload
    try:
        event_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from None

    event_type = x_github_event
    logger.info(f"Received {event_type} event (delivery: {x_github_delivery})")

    # Process based on event type
    if event_type == "issues":
        intent = detect_intent(event_data)
        if intent:
            logger.info(
                f"Detected intent: {intent} for issue #{event_data.get('issue', {}).get('number')}"
            )
            # In production: apply agent:queued label via GitHub API
            # For now, just log the detection
        else:
            logger.info("Event not actionable - no intent detected")

    # Respond within GitHub's 10-second timeout
    return WebhookResponse(
        status="accepted",
        message=f"Event {x_github_delivery} received and processed",
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "notifier"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with service information."""
    return {
        "service": "workflow-orchestration-queue Notifier",
        "version": "0.1.0",
        "docs": "/docs",
    }


def main() -> None:
    """Entry point for running the notifier service."""
    import uvicorn

    uvicorn.run(
        "src.notifier_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
