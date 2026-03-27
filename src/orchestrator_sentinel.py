"""Background polling service - "The Brain".

This service polls GitHub for queued work items, claims them using
distributed locking, and dispatches workers via the shell bridge.
"""

import asyncio
import logging
import os
import signal

from pydantic_settings import BaseSettings

from src.models.work_item import WorkItem, WorkItemStatus
from src.queue.github_queue import GitHubQueue

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    github_token: str = ""
    repo_slug: str = ""
    sentinel_bot_login: str = "sentinel-bot[bot]"
    sentinel_id: str = ""
    poll_interval: int = 60
    prompt_timeout: int = 5700  # 95 minutes
    heartbeat_interval: int = 300  # 5 minutes
    max_backoff: int = 960  # 16 minutes
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class Sentinel:
    """Orchestrator sentinel service.

    Polls for work, claims tasks, dispatches workers, and manages
    the lifecycle of work items through the queue.
    """

    def __init__(self) -> None:
        """Initialize the sentinel service."""
        self.queue = GitHubQueue(
            repo_slug=settings.repo_slug,
            github_token=settings.github_token,
        )
        self.running = True
        self.current_item: WorkItem | None = None
        self.current_backoff = settings.poll_interval
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the sentinel polling loop."""
        logger.info(f"Sentinel {settings.sentinel_id} starting")
        logger.info(f"Polling interval: {settings.poll_interval}s")
        logger.info(f"Repository: {settings.repo_slug}")

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        try:
            await self._poll_loop()
        except Exception as e:
            logger.exception(f"Fatal error in poll loop: {e}")
            raise
        finally:
            logger.info("Sentinel shutdown complete")

    def _handle_shutdown(self) -> None:
        """Handle graceful shutdown signals."""
        logger.info("Shutdown signal received - finishing current task")
        self.running = False
        self._shutdown_event.set()

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self.running:
            try:
                await self._poll_and_process()
                self.current_backoff = settings.poll_interval
            except Exception as e:
                logger.error(f"Poll error: {e}")
                await self._backoff()

            if self.running:
                await asyncio.sleep(self.current_backoff)

    async def _poll_and_process(self) -> None:
        """Poll for work items and process them."""
        items = await self.queue.get_queued_items()

        if not items:
            logger.debug("No queued items found")
            return

        logger.info(f"Found {len(items)} queued items")

        for item in items:
            if not self.running:
                break

            if await self._process_item(item):
                # Only process one item at a time
                break

    async def _process_item(self, item: WorkItem) -> bool:
        """Process a single work item.

        Args:
            item: The work item to process.

        Returns:
            True if item was claimed and processed, False otherwise.
        """
        # Try to claim the item
        if not await self.queue.claim_item(item, settings.sentinel_bot_login):
            logger.info(f"Failed to claim item {item.id} - already claimed")
            return False

        self.current_item = item
        logger.info(f"Claimed item {item.id}: {item.metadata.get('title', 'N/A')}")

        try:
            # Run the worker
            exit_code = await self._dispatch_worker(item)

            # Update status based on result
            if exit_code == 0:
                await self.queue.update_status(
                    item,
                    WorkItemStatus.SUCCESS,
                    comment=f"✅ Task completed successfully by {settings.sentinel_id}",
                )
            else:
                await self.queue.update_status(
                    item,
                    WorkItemStatus.ERROR,
                    comment=f"❌ Task failed with exit code {exit_code}",
                )

        except Exception as e:
            logger.exception(f"Worker dispatch failed: {e}")
            await self.queue.update_status(
                item,
                WorkItemStatus.INFRA_FAILURE,
                comment=f"⚠️ Infrastructure error: {str(e)[:500]}",
            )

        finally:
            self.current_item = None

        return True

    async def _dispatch_worker(self, item: WorkItem) -> int:
        """Dispatch the worker via shell bridge.

        Args:
            item: The work item to process.

        Returns:
            Exit code from the worker.
        """
        logger.info(f"Dispatching worker for item {item.id}")

        # Run shell bridge commands
        commands = [
            ("up", 300),  # Provision
            ("start", 60),  # Start server
            ("prompt", settings.prompt_timeout),  # Execute
            ("stop", 60),  # Cleanup
        ]

        for cmd, timeout in commands:
            logger.info(f"Running: devcontainer-opencode.sh {cmd}")
            try:
                result = await asyncio.wait_for(
                    self._run_shell_command(cmd, item),
                    timeout=timeout,
                )
                if result != 0 and cmd == "prompt":
                    return result
            except TimeoutError:
                logger.error(f"Command {cmd} timed out after {timeout}s")
                return 124  # Timeout exit code

        return 0

    async def _run_shell_command(self, command: str, item: WorkItem) -> int:
        """Run a shell bridge command.

        Args:
            command: The command to run (up, start, prompt, stop).
            item: The work item being processed.

        Returns:
            Exit code from the command.
        """
        script_path = "scripts/devcontainer-opencode.sh"

        env = os.environ.copy()
        env["WORK_ITEM_ID"] = item.id
        env["WORK_ITEM_BODY"] = item.context_body[:10000]  # Limit size

        try:
            proc = await asyncio.create_subprocess_exec(
                "bash",
                script_path,
                command,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if stdout:
                logger.debug(f"stdout: {stdout.decode()[:1000]}")
            if stderr:
                logger.debug(f"stderr: {stderr.decode()[:1000]}")

            return proc.returncode or 0

        except Exception as e:
            logger.error(f"Failed to run command {command}: {e}")
            return 1

    async def _backoff(self) -> None:
        """Apply exponential backoff on errors."""
        self.current_backoff = min(self.current_backoff * 2, settings.max_backoff)
        logger.warning(f"Backing off for {self.current_backoff}s")
        await asyncio.sleep(self.current_backoff)


async def main_async() -> None:
    """Async entry point."""
    sentinel = Sentinel()
    await sentinel.start()


def main() -> None:
    """Entry point for running the sentinel service."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
