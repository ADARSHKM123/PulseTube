"""Pipeline status, run history, quota meter, and the manual run trigger."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_session
from ..models import PipelineRun, TrackedKeyword, Transcript, Video
from ..schemas import ConfigOut, QuotaOut, RunOut, StatusOut, TotalsOut
from ..services.pipeline import pipeline_is_running, run_pipeline
from ..services.youtube import quota_used_today
from ..utils import quota_day_today
from ..workers.scheduler import next_run_time

router = APIRouter()


@router.get("/system/status", response_model=StatusOut)
async def system_status(db: AsyncSession = Depends(get_session)):
    settings = get_settings()
    last_run = (
        await db.execute(select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1))
    ).scalar_one_or_none()

    used = await quota_used_today(db)
    videos = (await db.execute(select(func.count()).select_from(Video))).scalar() or 0
    active_kw = (
        await db.execute(
            select(func.count()).select_from(TrackedKeyword).where(TrackedKeyword.is_active.is_(True))
        )
    ).scalar() or 0
    transcripts_ok = (
        await db.execute(select(func.count()).select_from(Transcript).where(Transcript.status == "ok"))
    ).scalar() or 0
    with_sentiment = (
        await db.execute(
            select(func.count()).select_from(Video).where(Video.sentiment_positive_pct.isnot(None))
        )
    ).scalar() or 0

    return StatusOut(
        pipeline_running=pipeline_is_running(),
        last_run=RunOut.model_validate(last_run) if last_run else None,
        next_run_at=next_run_time(),
        quota=QuotaOut(
            date=quota_day_today(),
            used=used,
            limit=settings.daily_quota_limit,
            budget=settings.quota_budget,
            remaining=max(0, settings.quota_budget - used),
        ),
        totals=TotalsOut(
            videos=videos, active_keywords=active_kw, transcripts_ok=transcripts_ok, with_sentiment=with_sentiment
        ),
        config=ConfigOut(
            interval_minutes=settings.pipeline_interval_minutes,
            keywords_per_run=settings.search_keywords_per_run,
            search_order=settings.search_order,
            region_code=settings.region_code,
            published_within_days=settings.search_published_within_days,
            transcript_provider=settings.transcript_provider,
            api_key_configured=bool(settings.youtube_api_key),
        ),
    )


@router.get("/system/runs", response_model=list[RunOut])
async def list_runs(limit: int = Query(30, ge=1, le=200), db: AsyncSession = Depends(get_session)):
    runs = (
        (await db.execute(select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)))
        .scalars()
        .all()
    )
    return [RunOut.model_validate(r) for r in runs]


@router.post("/system/run", status_code=202)
async def trigger_run():
    """Kick an ingestion cycle right now (same code path as the scheduler)."""
    if not get_settings().youtube_api_key:
        raise HTTPException(
            status_code=400,
            detail="YOUTUBE_API_KEY is not configured — add it to backend/.env and restart",
        )
    if pipeline_is_running():
        raise HTTPException(status_code=409, detail="A pipeline run is already in progress")
    asyncio.create_task(run_pipeline(trigger="manual"))
    return {"started": True}
