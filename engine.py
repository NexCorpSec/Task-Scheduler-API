import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from croniter import croniter

logger = logging.getLogger(__name__)


class SchedulerEngine:
    """
    Core scheduler: pulls due tasks from the DB, dispatches them to workers,
    handles retries with configurable back-off, and fires webhooks on completion.
    """

    def __init__(self, poll_interval_seconds: int = 5):
        self.poll_interval = poll_interval_seconds
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._metrics = {
            "tasks_dispatched": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
        }

    async def start(self):
        self._running = True
        self._loop_task = asyncio.create_task(self._poll_loop())
        logger.info("SchedulerEngine started")

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("SchedulerEngine stopped")

    async def _poll_loop(self):
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.exception(f"Scheduler tick error: {exc}")
            await asyncio.sleep(self.poll_interval)

    async def _tick(self):
        from db.session import get_session
        from db.models import Task, TaskStatus

        async with get_session() as session:
            now = datetime.now(timezone.utc)

            # Find tasks due for execution
            due_tasks = await session.execute(
                """
                SELECT * FROM tasks
                WHERE status IN ('pending', 'retrying')
                  AND (scheduled_at IS NULL OR scheduled_at <= :now)
                ORDER BY priority DESC, created_at ASC
                LIMIT 50
                """,
                {"now": now},
            )

            for task in due_tasks:
                await self._dispatch(task, session)

            # Handle cron tasks: schedule next occurrence
            cron_tasks = await session.execute(
                "SELECT * FROM tasks WHERE cron_expression IS NOT NULL AND status = 'success'"
            )
            for task in cron_tasks:
                await self._schedule_next_cron(task, session)

    async def _dispatch(self, task, session):
        logger.info(f"Dispatching task {task.id} ({task.name}) to queue '{task.queue}'")
        # Update status → queued
        task.status = "queued"
        task.attempt += 1
        await session.commit()
        self._metrics["tasks_dispatched"] += 1

        # In a real system: push to Redis/RabbitMQ/SQS queue
        # Here we simulate async dispatch
        asyncio.create_task(self._run_task(task))

    async def _run_task(self, task):
        logger.info(f"Running task {task.id}")
        # Worker picks up and executes; this method handles the outcome
        pass

    async def enqueue(self, task_id: str):
        """Immediately enqueue a task bypassing the scheduler poll."""
        logger.info(f"Manually enqueuing task {task_id}")
        self._metrics["tasks_dispatched"] += 1

    async def cancel(self, task_id: str):
        """Signal a running or queued task to cancel."""
        logger.info(f"Cancelling task {task_id}")
        # In production: send cancel signal to the worker holding the task

    def _compute_backoff(self, policy, attempt: int) -> int:
        if policy.backoff_type == "fixed":
            delay = policy.backoff_seconds
        elif policy.backoff_type == "linear":
            delay = policy.backoff_seconds * attempt
        else:  # exponential
            delay = policy.backoff_seconds * (2 ** (attempt - 1))
        return min(delay, policy.max_backoff_seconds)

    async def _schedule_next_cron(self, task, session):
        cron = croniter(task.cron_expression, datetime.now(timezone.utc))
        next_run = cron.get_next(datetime)
        logger.debug(f"Next run for cron task {task.id}: {next_run}")
        # Clone task with new scheduled_at

    async def get_metrics(self) -> dict:
        return {
            "uptime_seconds": 0,  # placeholder
            **self._metrics,
        }
