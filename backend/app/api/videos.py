"""Per-video detail: full metadata, metric history, transcript, sentiment,
on-demand live refresh, and untracking."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..database import get_session
from ..models import MetricsSnapshot, SentimentAnalysis, Transcript, Video
from ..schemas import MetricsPoint, SentimentOut, TranscriptOut, VideoDetail
from ..services.pipeline import refresh_single_video
from ..services.youtube import QuotaBudgetExhausted, QuotaExceededError, YouTubeAPIError

router = APIRouter()


async def _get_video(db: AsyncSession, video_id: str) -> Video:
    video = await db.get(Video, video_id, options=[selectinload(Video.discovered_keyword)])
    if video is None:
        raise HTTPException(status_code=404, detail="Video is not being tracked")
    return video


async def _detail(db: AsyncSession, video: Video) -> VideoDetail:
    detail = VideoDetail.model_validate(video)
    if video.discovered_keyword is not None:
        detail.keyword = video.discovered_keyword.keyword

    latest = (
        await db.execute(
            select(SentimentAnalysis)
            .where(SentimentAnalysis.video_id == video.video_id)
            .order_by(SentimentAnalysis.computed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    # Zero-comment rows are backoff markers, not real analyses
    if latest is not None and latest.comments_analyzed > 0:
        detail.sentiment = SentimentOut.model_validate(latest)
    return detail


@router.get("/videos/{video_id}", response_model=VideoDetail)
async def get_video(video_id: str, db: AsyncSession = Depends(get_session)):
    video = await _get_video(db, video_id)
    return await _detail(db, video)


@router.get("/videos/{video_id}/history", response_model=list[MetricsPoint])
async def get_history(video_id: str, db: AsyncSession = Depends(get_session)):
    await _get_video(db, video_id)
    rows = (
        (
            await db.execute(
                select(MetricsSnapshot)
                .where(MetricsSnapshot.video_id == video_id)
                .order_by(MetricsSnapshot.captured_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return [MetricsPoint.model_validate(r) for r in rows]


@router.get("/videos/{video_id}/transcript", response_model=TranscriptOut)
async def get_transcript(video_id: str, db: AsyncSession = Depends(get_session)):
    video = await _get_video(db, video_id)
    tr = await db.get(Transcript, video_id)
    if tr is None:
        # Not attempted yet — the next pipeline cycle will pick it up
        return TranscriptOut(video_id=video_id, status=video.transcript_status or "pending")
    return TranscriptOut.model_validate(tr, from_attributes=True)


@router.post("/videos/{video_id}/refresh", response_model=VideoDetail)
async def refresh_video(video_id: str, db: AsyncSession = Depends(get_session)):
    """Live re-pull of metrics + comments for one video (~2 quota units)."""
    if not get_settings().youtube_api_key:
        raise HTTPException(status_code=400, detail="YOUTUBE_API_KEY is not configured on the backend")
    video = await _get_video(db, video_id)
    try:
        video = await refresh_single_video(db, video)
    except (QuotaBudgetExhausted, QuotaExceededError) as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except YouTubeAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return await _detail(db, video)


@router.delete("/videos/{video_id}", status_code=204)
async def untrack_video(video_id: str, db: AsyncSession = Depends(get_session)):
    """Remove a video and its history/transcript/sentiment from tracking."""
    video = await _get_video(db, video_id)
    await db.delete(video)
    await db.commit()
