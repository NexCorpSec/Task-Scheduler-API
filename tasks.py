from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Optional, List
from schemas import TaskCreate, TaskUpdate, TaskResponse, TaskStatus
from db.repositories.task_repository import TaskRepository
from scheduler.engine import SchedulerEngine
from dependencies import get_task_repo, get_scheduler

router = APIRouter()


@router.get("", response_model=dict)
async def list_tasks(
    queue: Optional[str] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    repo: TaskRepository = Depends(get_task_repo),
):
    """List tasks with optional filtering by queue, status, or tag."""
    result = await repo.list(
        queue=queue,
        status=status,
        tag=tag,
        page=page,
        per_page=per_page,
    )
    return result


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    background_tasks: BackgroundTasks,
    repo: TaskRepository = Depends(get_task_repo),
    scheduler: SchedulerEngine = Depends(get_scheduler),
):
    """Create and optionally schedule a new task."""
    task = await repo.create(body)

    if body.scheduled_at is None and body.cron_expression is None:
        # Enqueue immediately
        background_tasks.add_task(scheduler.enqueue, task.id)

    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, repo: TaskRepository = Depends(get_task_repo)):
    """Get a single task by ID."""
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    repo: TaskRepository = Depends(get_task_repo),
):
    """Update a pending or scheduled task."""
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in (TaskStatus.pending, TaskStatus.queued):
        raise HTTPException(status_code=409, detail=f"Cannot update a task in '{task.status}' state")

    updated = await repo.update(task_id, body)
    return updated


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    repo: TaskRepository = Depends(get_task_repo),
    scheduler: SchedulerEngine = Depends(get_scheduler),
):
    """Cancel a pending, queued, or running task."""
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in (TaskStatus.success, TaskStatus.cancelled):
        raise HTTPException(status_code=409, detail=f"Task is already {task.status}")

    cancelled = await scheduler.cancel(task_id)
    return cancelled


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    repo: TaskRepository = Depends(get_task_repo),
    scheduler: SchedulerEngine = Depends(get_scheduler),
):
    """Manually trigger a retry for a failed task."""
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.failed:
        raise HTTPException(status_code=409, detail="Only failed tasks can be retried")

    retried = await repo.reset_for_retry(task_id)
    background_tasks.add_task(scheduler.enqueue, task_id)
    return retried


@router.get("/{task_id}/logs", response_model=List[dict])
async def get_task_logs(
    task_id: str,
    repo: TaskRepository = Depends(get_task_repo),
):
    """Fetch execution logs for a task."""
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    logs = await repo.get_logs(task_id)
    return logs


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    repo: TaskRepository = Depends(get_task_repo),
):
    """Delete a task (only completed or cancelled tasks)."""
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in (TaskStatus.pending, TaskStatus.queued, TaskStatus.running):
        raise HTTPException(status_code=409, detail="Cannot delete an active task — cancel it first")

    await repo.delete(task_id)
