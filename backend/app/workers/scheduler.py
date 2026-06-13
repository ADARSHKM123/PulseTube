"""APScheduler-driven automation: the spec's 8–12 daily ingestion runs.

Runs inside the FastAPI process (AsyncIOScheduler shares the event loop),
so a single `uvicorn` invocation is the whole backend — no separate
Celery broker to operate.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..config import get_settings
from ..services.pipeline import run_pipeline
from ..utils import utcnow

logger = logging.getLogger("pulsetube.scheduler")

JOB_ID = "ingestion-cycle"
scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    settings = get_settings()
    interval = max(30, settings.pipeline_interval_minutes)  # floor: 48 runs/day max
    first_fire = utcnow() + (
        timedelta(seconds=20) if settings.run_pipeline_on_startup else timedelta(minutes=interval)
    )
    scheduler.add_job(
        run_pipeline,
        IntervalTrigger(minutes=interval, jitter=120),
        kwargs={"trigger": "scheduled"},
        id=JOB_ID,
        coalesce=True,          # collapse missed runs (laptop slept) into one
        max_instances=1,        # never overlap cycles
        misfire_grace_time=3600,
        next_run_time=first_fire,
    )
    scheduler.start()
    logger.info("scheduler started: every %s min, first run at %s", interval, first_fire.isoformat())


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def next_run_time() -> datetime | None:
    if not scheduler.running:
        return None
    job = scheduler.get_job(JOB_ID)
    return job.next_run_time if job else None
