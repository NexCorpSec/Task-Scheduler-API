from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import re


class TaskStatus(str, Enum):
    pending   = "pending"
    queued    = "queued"
    running   = "running"
    success   = "success"
    failed    = "failed"
    cancelled = "cancelled"
    retrying  = "retrying"


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_type: str = Field(default="exponential", pattern="^(fixed|linear|exponential)$")
    backoff_seconds: int = Field(default=60, ge=1)
    max_backoff_seconds: int = Field(default=3600, ge=1)


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    queue: str = Field(default="default")
    payload: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    priority: int = Field(default=5, ge=1, le=10)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    tags: List[str] = Field(default_factory=list)
    webhook_url: Optional[str] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v):
        if v is None:
            return v
        parts = v.strip().split()
        if len(parts) not in (5, 6):
            raise ValueError("Cron expression must have 5 or 6 fields")
        return v


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=10)
    retry_policy: Optional[RetryPolicy] = None
    tags: Optional[List[str]] = None
    webhook_url: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    name: str
    queue: str
    status: TaskStatus
    payload: Dict[str, Any]
    scheduled_at: Optional[datetime]
    cron_expression: Optional[str]
    timeout_seconds: int
    priority: int
    retry_policy: RetryPolicy
    attempt: int
    tags: List[str]
    webhook_url: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class QueueStats(BaseModel):
    name: str
    pending: int
    running: int
    failed: int
    success: int
    workers_active: int
    throughput_per_min: float


class WorkerResponse(BaseModel):
    id: str
    queue: str
    status: str  # idle | busy | draining | offline
    current_task_id: Optional[str]
    tasks_processed: int
    tasks_failed: int
    started_at: datetime
    last_heartbeat: datetime
