"""The ingestion pipeline — one full cycle of the spec's Phases A→C (+ transcripts).

A: round-robin keyword search (search.list, the expensive call)
B: batched metrics refresh for every video still in the tracking window
C: comment mining → VADER sentiment for videos due a refresh
D: transcript fetching (free — no YouTube quota involved)

Each phase commits its own progress so a quota halt mid-run keeps
everything gathered up to that point.
"""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import session_scope
from ..models import MetricsSnapshot, PipelineRun, SentimentAnalysis, TrackedKeyword, Transcript, Video
from ..utils import ensure_utc, utcnow
from .sentiment import analyze_comments
from .transcripts import get_transcript_provider
from .youtube import (
    QuotaBudgetExhausted,
    QuotaExceededError,
    YouTubeAPIError,
    YouTubeClient,
    parse_iso8601_duration,
    pick_best_thumbnail,
)

logger = logging.getLogger("pulsetube.pipeline")

# Per-run caps keep a single cycle's spend predictable:
#   search: keywords_per_run × 100u   sentiment: ≤75u   metrics: ~1u per 50 videos
SENTIMENT_MAX_PER_RUN = 75
SENTIMENT_REFRESH_HOURS = 24
TRANSCRIPTS_MAX_PER_RUN = 40
TRANSCRIPT_ERROR_RETRY_HOURS = 6
TRANSCRIPT_UNAVAILABLE_RETRY_HOURS = 24
# Captions for brand-new uploads often appear hours later; stop re-checking
# caption-less videos once they are this old.
TRANSCRIPT_GIVE_UP_DAYS = 7

_pipeline_lock = asyncio.Lock()


def pipeline_is_running() -> bool:
    return _pipeline_lock.locked()


def apply_video_item(
    db: AsyncSession,
    item: dict,
    existing: Video | None,
    discovered_keyword_id: int | None,
    prev_capture_at,
) -> Video:
    """Upsert one videos.list item: metadata, a new history point, and the
    denormalized latest-metrics columns the dashboard filters/sorts on."""
    now = utcnow()
    snippet = item.get("snippet", {}) or {}
    stats = item.get("statistics", {}) or {}
    content = item.get("contentDetails", {}) or {}

    views = int(stats.get("viewCount", 0) or 0)
    likes = int(stats.get("likeCount", 0) or 0)  # absent when the channel hides likes
    comments = int(stats.get("commentCount", 0) or 0)

    published_raw = snippet.get("publishedAt")
    published_at = None
    if published_raw:
        from datetime import datetime

        try:
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
        except ValueError:
            published_at = None

    if existing is None:
        video = Video(
            video_id=item["id"],
            discovered_keyword_id=discovered_keyword_id,
            first_seen_at=now,
        )
        db.add(video)
    else:
        video = existing
        prev_views = video.latest_view_count
        prev_likes = video.latest_like_count
        prev_at = ensure_utc(prev_capture_at)
        if prev_at is not None:
            hours = (now - prev_at).total_seconds() / 3600
            # Sub-6-minute gaps (e.g. manual refresh right after a run) make
            # velocity numbers meaningless noise — keep the previous value.
            if hours >= 0.1:
                video.view_velocity = round((views - prev_views) / hours, 2)
                video.like_velocity = round((likes - prev_likes) / hours, 2)

    video.title = snippet.get("title", video.title if existing else "") or ""
    video.description = (snippet.get("description") or "")[:5000]
    video.channel_id = snippet.get("channelId", "") or ""
    video.channel_title = snippet.get("channelTitle", "") or ""
    video.published_at = published_at
    video.thumbnail_url = pick_best_thumbnail(snippet.get("thumbnails"))
    video.duration_seconds = parse_iso8601_duration(content.get("duration"))
    video.tags = (snippet.get("tags") or [])[:20] or None
    video.latest_view_count = views
    video.latest_like_count = likes
    video.latest_comment_count = comments
    video.like_ratio = round(likes / views * 100, 3) if views > 0 and likes > 0 else None
    video.last_refreshed_at = now

    db.add(MetricsSnapshot(video_id=item["id"], captured_at=now, view_count=views, like_count=likes, comment_count=comments))
    return video


async def compute_sentiment(db: AsyncSession, yt: YouTubeClient, video: Video, max_comments: int) -> bool:
    """Fetch top comment threads and store an aggregate sentiment row.
    Returns True when real comments were analyzed."""
    comments = await yt.list_comment_threads(video.video_id, max_comments)
    result = analyze_comments(comments)
    if result is None:
        # Comments disabled/empty — store a zero-row so the 24h refresh
        # policy stops re-spending quota on this video every cycle.
        db.add(SentimentAnalysis(video_id=video.video_id, comments_analyzed=0, sample_comments=None))
        return False

    db.add(
        SentimentAnalysis(
            video_id=video.video_id,
            comments_analyzed=result["comments_analyzed"],
            positive_pct=result["positive_pct"],
            negative_pct=result["negative_pct"],
            neutral_pct=result["neutral_pct"],
            avg_compound=result["avg_compound"],
            sample_comments=result["sample_comments"],
        )
    )
    video.sentiment_positive_pct = result["positive_pct"]
    video.sentiment_negative_pct = result["negative_pct"]
    video.sentiment_neutral_pct = result["neutral_pct"]
    video.sentiment_compound = result["avg_compound"]
    return True


async def _phase_search(db: AsyncSession, yt: YouTubeClient, run: PipelineRun, errors: list[str]) -> dict[str, int]:
    """Phase A — search the least-recently-searched active keywords (round-robin
    keeps every keyword fresh while bounding the 100-unit search spend per run)."""
    settings = get_settings()
    keywords = (
        (
            await db.execute(
                select(TrackedKeyword)
                .where(TrackedKeyword.is_active.is_(True))
                .order_by(TrackedKeyword.last_searched_at.asc().nulls_first())
                .limit(settings.search_keywords_per_run)
            )
        )
        .scalars()
        .all()
    )

    discovered: dict[str, int] = {}  # video_id -> keyword that first surfaced it
    searched_names = []
    for kw in keywords:
        ids = await yt.search_videos(kw.keyword)
        kw.last_searched_at = utcnow()
        kw.search_count += 1
        searched_names.append(kw.keyword)
        for vid in ids:
            discovered.setdefault(vid, kw.id)

    run.keywords_searched = searched_names
    await db.commit()

    if not discovered:
        return {}
    existing = set(
        (await db.execute(select(Video.video_id).where(Video.video_id.in_(discovered.keys())))).scalars().all()
    )
    return {vid: kw_id for vid, kw_id in discovered.items() if vid not in existing}


async def _phase_metrics(db: AsyncSession, yt: YouTubeClient, run: PipelineRun, new_videos: dict[str, int], errors: list[str]) -> None:
    """Phase B — one batched videos.list sweep over new discoveries plus every
    video inside the refresh window. 50 videos per quota unit."""
    settings = get_settings()
    cutoff = utcnow() - timedelta(days=settings.metrics_refresh_window_days)
    tracked_ids = (
        (await db.execute(select(Video.video_id).where(Video.first_seen_at >= cutoff))).scalars().all()
    )
    target_ids = list(dict.fromkeys([*new_videos.keys(), *tracked_ids]))
    if not target_ids:
        return

    # Previous capture time per video — the basis for velocity computation.
    prev_rows = await db.execute(
        select(MetricsSnapshot.video_id, func.max(MetricsSnapshot.captured_at))
        .where(MetricsSnapshot.video_id.in_(target_ids))
        .group_by(MetricsSnapshot.video_id)
    )
    prev_capture = dict(prev_rows.all())

    items = await yt.list_videos(target_ids)
    existing_map = {
        v.video_id: v
        for v in (await db.execute(select(Video).where(Video.video_id.in_([i["id"] for i in items])))).scalars()
    }

    for item in items:
        try:
            vid = item["id"]
            existing = existing_map.get(vid)
            apply_video_item(db, item, existing, new_videos.get(vid), prev_capture.get(vid))
            if existing is None:
                run.videos_discovered += 1
            run.videos_refreshed += 1
        except Exception as exc:  # one malformed item must not sink the sweep
            errors.append(f"metrics {item.get('id', '?')}: {exc!r}")
    await db.commit()


async def _phase_sentiment(db: AsyncSession, yt: YouTubeClient, run: PipelineRun, errors: list[str]) -> None:
    """Phase C — comment mining + VADER for videos lacking fresh sentiment."""
    settings = get_settings()
    cutoff = utcnow() - timedelta(days=settings.metrics_refresh_window_days)

    last_computed = dict(
        (
            await db.execute(
                select(SentimentAnalysis.video_id, func.max(SentimentAnalysis.computed_at)).group_by(
                    SentimentAnalysis.video_id
                )
            )
        ).all()
    )

    candidates = (
        (
            await db.execute(
                select(Video)
                .where(Video.first_seen_at >= cutoff, Video.latest_comment_count > 0)
                .order_by(Video.latest_view_count.desc())
            )
        )
        .scalars()
        .all()
    )

    stale_before = utcnow() - timedelta(hours=SENTIMENT_REFRESH_HOURS)
    due = []
    for v in candidates:
        last = ensure_utc(last_computed.get(v.video_id))
        if last is None or last < stale_before:
            due.append(v)
        if len(due) >= SENTIMENT_MAX_PER_RUN:
            break

    for video in due:
        try:
            analyzed = await compute_sentiment(db, yt, video, settings.comments_max_per_video)
            run.sentiment_computed += 1
            if analyzed:
                run.comments_fetched += min(video.latest_comment_count, settings.comments_max_per_video)
            await db.commit()
        except (QuotaBudgetExhausted, QuotaExceededError):
            await db.rollback()
            raise
        except YouTubeAPIError as exc:
            await db.rollback()
            errors.append(f"sentiment {video.video_id}: {exc}")


async def _phase_transcripts(db: AsyncSession, run: PipelineRun, errors: list[str]) -> None:
    """Phase D — transcripts via the configured provider. Zero YouTube quota;
    bounded concurrency keeps the free library under IP rate-limit radar."""
    settings = get_settings()
    cutoff = utcnow() - timedelta(days=settings.metrics_refresh_window_days)
    now = utcnow()

    rows = (
        await db.execute(
            select(Video, Transcript)
            .outerjoin(Transcript, Transcript.video_id == Video.video_id)
            .where(Video.first_seen_at >= cutoff, Video.transcript_status != "ok")
        )
    ).all()

    due: list[Video] = []
    for video, tr in rows:
        if tr is None:
            due.append(video)
            continue
        fetched_at = ensure_utc(tr.fetched_at) or now
        age_hours = (now - fetched_at).total_seconds() / 3600
        published = ensure_utc(video.published_at)
        too_old_to_retry = published is not None and (now - published).days > TRANSCRIPT_GIVE_UP_DAYS
        if tr.status == "error" and age_hours >= TRANSCRIPT_ERROR_RETRY_HOURS:
            due.append(video)
        elif tr.status == "unavailable" and age_hours >= TRANSCRIPT_UNAVAILABLE_RETRY_HOURS and not too_old_to_retry:
            due.append(video)
        if len(due) >= TRANSCRIPTS_MAX_PER_RUN:
            break
    due = due[:TRANSCRIPTS_MAX_PER_RUN]
    if not due:
        return

    provider = get_transcript_provider()
    semaphore = asyncio.Semaphore(max(1, settings.transcript_concurrency))

    async def fetch_one(video: Video):
        async with semaphore:
            return video, await provider.fetch(video.video_id)

    results = await asyncio.gather(*(fetch_one(v) for v in due), return_exceptions=True)
    for res in results:
        if isinstance(res, BaseException):
            errors.append(f"transcript task: {res!r}")
            continue
        video, result = res
        tr = await db.get(Transcript, video.video_id)
        if tr is None:
            tr = Transcript(video_id=video.video_id)
            db.add(tr)
        tr.status = result.status
        tr.language = result.language
        tr.source = result.source
        tr.content = result.text
        tr.word_count = result.word_count
        tr.fetched_at = utcnow()
        video.transcript_status = result.status
        if result.status == "ok":
            run.transcripts_fetched += 1
    await db.commit()


async def run_pipeline(trigger: str = "scheduled") -> int | None:
    """Execute one full ingestion cycle. Returns the run id, or None when a
    cycle is already in flight (scheduler overlap, double manual trigger)."""
    if _pipeline_lock.locked():
        logger.warning("pipeline already running; skipping %s trigger", trigger)
        return None

    async with _pipeline_lock:
        async with session_scope() as db:
            run = PipelineRun(trigger=trigger)
            db.add(run)
            await db.commit()
            await db.refresh(run)
            logger.info("pipeline run %s started (%s)", run.id, trigger)

            yt = YouTubeClient(db)
            errors: list[str] = []
            halted = False
            fatal = False
            try:
                new_videos: dict[str, int] = {}
                try:
                    new_videos = await _phase_search(db, yt, run, errors)
                except (QuotaBudgetExhausted, QuotaExceededError) as exc:
                    await db.rollback()
                    halted = True
                    errors.append(f"halted during search: {exc}")
                except Exception as exc:
                    await db.rollback()
                    errors.append(f"search phase: {exc!r}")

                if not halted:
                    try:
                        await _phase_metrics(db, yt, run, new_videos, errors)
                    except (QuotaBudgetExhausted, QuotaExceededError) as exc:
                        await db.rollback()
                        halted = True
                        errors.append(f"halted during metrics: {exc}")
                    except Exception as exc:
                        await db.rollback()
                        errors.append(f"metrics phase: {exc!r}")

                if not halted:
                    try:
                        await _phase_sentiment(db, yt, run, errors)
                    except (QuotaBudgetExhausted, QuotaExceededError) as exc:
                        halted = True
                        errors.append(f"halted during sentiment: {exc}")
                    except Exception as exc:
                        await db.rollback()
                        errors.append(f"sentiment phase: {exc!r}")

                # Transcripts cost no YouTube quota — run them even when halted.
                try:
                    await _phase_transcripts(db, run, errors)
                except Exception as exc:
                    await db.rollback()
                    errors.append(f"transcript phase: {exc!r}")
            except Exception as exc:
                fatal = True
                await db.rollback()
                errors.append(f"fatal: {exc!r}")
                logger.exception("pipeline run %s fatal error", run.id)
            finally:
                await yt.close()
                run.finished_at = utcnow()
                run.quota_units_used = yt.units_used
                if fatal:
                    run.status = "failed"
                elif halted:
                    run.status = "halted_quota"
                elif errors:
                    run.status = "partial"
                else:
                    run.status = "success"
                run.error = "\n".join(errors[:25]) or None
                await db.commit()
                logger.info(
                    "pipeline run %s finished: %s (%s units, +%s videos, %s refreshed)",
                    run.id, run.status, run.quota_units_used, run.videos_discovered, run.videos_refreshed,
                )
            return run.id


async def refresh_single_video(db: AsyncSession, video: Video) -> Video:
    """On-demand refresh from the detail view: ~2 quota units (metrics + comments)."""
    settings = get_settings()
    yt = YouTubeClient(db)
    try:
        prev = await db.execute(
            select(func.max(MetricsSnapshot.captured_at)).where(MetricsSnapshot.video_id == video.video_id)
        )
        items = await yt.list_videos([video.video_id])
        if not items:
            raise YouTubeAPIError("Video no longer available on YouTube")
        video = apply_video_item(db, items[0], video, video.discovered_keyword_id, prev.scalar())
        await compute_sentiment(db, yt, video, settings.comments_max_per_video)
        await db.commit()
        return video
    finally:
        await yt.close()
