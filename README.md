# task-scheduler-api

A FastAPI-based task scheduler with queues, workers, cron jobs, retry policies, and webhook notifications.

## Stack
- Python 3.12+
- FastAPI + Uvicorn
- SQLAlchemy (async) + PostgreSQL
- Croniter for cron expression parsing

## Quickstart

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/scheduler
uvicorn main:app --reload
```

Swagger UI: http://localhost:8000/docs

## Features

- **Immediate tasks** — enqueue and run right away
- **Scheduled tasks** — run at a specific datetime
- **Cron tasks** — repeat on a cron schedule
- **Priority queues** — 1–10 priority levels
- **Retry policies** — fixed / linear / exponential backoff
- **Webhooks** — POST to a URL on task success or failure
- **Worker management** — monitor active workers and throughput
- **Metrics** — live stats via `/metrics`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/tasks | List tasks |
| POST | /api/v1/tasks | Create task |
| GET | /api/v1/tasks/:id | Get task |
| PATCH | /api/v1/tasks/:id | Update task |
| POST | /api/v1/tasks/:id/cancel | Cancel task |
| POST | /api/v1/tasks/:id/retry | Retry failed task |
| GET | /api/v1/tasks/:id/logs | Task execution logs |
| GET | /api/v1/queues | Queue stats |
| GET | /api/v1/workers | Active workers |
| GET | /metrics | Scheduler metrics |
