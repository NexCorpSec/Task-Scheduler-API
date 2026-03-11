from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import logging

from routers import tasks, queues, workers, webhooks
from scheduler.engine import SchedulerEngine
from db.session import init_db
from dependencies import get_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    engine = SchedulerEngine()
    await engine.start()
    app.state.scheduler = engine
    logger.info("Scheduler engine started")
    yield
    await engine.stop()
    logger.info("Scheduler engine stopped")


app = FastAPI(
    title="Task Scheduler API",
    description="Schedule, queue, and monitor background jobs with retry logic and webhooks.",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router,   prefix="/api/v1/tasks",   tags=["Tasks"])
app.include_router(queues.router,  prefix="/api/v1/queues",  tags=["Queues"])
app.include_router(workers.router, prefix="/api/v1/workers", tags=["Workers"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.1.0"}


@app.get("/metrics")
async def metrics(scheduler: SchedulerEngine = Depends(get_scheduler)):
    return await scheduler.get_metrics()
