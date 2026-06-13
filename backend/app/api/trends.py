"""Trends feed, advanced filtering, overview stats, and CSV export.

Filtering/sorting runs against the denormalized columns on
videos_snapshot, so every dashboard query is one cheap single-table
scan regardless of how much history accumulates.
"""

import csv
import io
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_session
from ..models import Video
from ..schemas import OverviewOut, TrendItem, TrendPage
from ..utils import utcnow

router = APIRouter()

SORT_COLUMNS = {
    "views": Video.latest_view_count,
    "likes": Video.latest_like_count,
    "comments": Video.latest_comment_count,
    "velocity": Video.view_velocity,
    "like_velocity": Video.like_velocity,
    "like_ratio": Video.like_ratio,
    "positive": Video.sentiment_positive_pct,
    "negative": Video.sentiment_negative_pct,
    "compound": Video.sentiment_compound,
    "published": Video.published_at,
    "first_seen": Video.first_seen_at,
    "title": Video.title,
}

EXPORT_MAX_ROWS = 5000


class TrendFilters:
    """Shared query-param dependency for the feed, table, and CSV export."""

    def __init__(
        self,
        q: str | None = Query(None, max_length=200, description="Search in title/channel"),
        keyword_id: int | None = None,
        min_views: int | None = Query(None, ge=0),
        min_likes: int | None = Query(None, ge=0),
        min_comments: int | None = Query(None, ge=0),
        min_like_ratio: float | None = Query(None, ge=0, le=100),
        min_positive_pct: float | None = Query(None, ge=0, le=100),
        max_negative_pct: float | None = Query(None, ge=0, le=100),
        min_velocity: float | None = None,
        published_within_days: int | None = Query(None, ge=1, le=365),
        has_transcript: bool | None = None,
        sort: str = "views",
        order: str = "desc",
    ):
        self.q = q.strip() if q else None
        self.keyword_id = keyword_id
        self.min_views = min_views
        self.min_likes = min_likes
        self.min_comments = min_comments
        self.min_like_ratio = min_like_ratio
        self.min_positive_pct = min_positive_pct
        self.max_negative_pct = max_negative_pct
        self.min_velocity = min_velocity
        self.published_within_days = published_within_days
        self.has_transcript = has_transcript
        self.sort = sort if sort in SORT_COLUMNS else "views"
        self.order = "asc" if order == "asc" else "desc"

    def apply(self, stmt: Select) -> Select:
        f = self
        if f.q:
            like = f"%{f.q}%"
            stmt = stmt.where(Video.title.ilike(like) | Video.channel_title.ilike(like))
        if f.keyword_id is not None:
            stmt = stmt.where(Video.discovered_keyword_id == f.keyword_id)
        if f.min_views is not None:
            stmt = stmt.where(Video.latest_view_count >= f.min_views)
        if f.min_likes is not None:
            stmt = stmt.where(Video.latest_like_count >= f.min_likes)
        if f.min_comments is not None:
            stmt = stmt.where(Video.latest_comment_count >= f.min_comments)
        if f.min_like_ratio is not None:
            stmt = stmt.where(Video.like_ratio >= f.min_like_ratio)
        if f.min_positive_pct is not None:
            stmt = stmt.where(Video.sentiment_positive_pct >= f.min_positive_pct)
        if f.max_negative_pct is not None:
            stmt = stmt.where(Video.sentiment_negative_pct <= f.max_negative_pct)
        if f.min_velocity is not None:
            stmt = stmt.where(Video.view_velocity >= f.min_velocity)
        if f.published_within_days is not None:
            stmt = stmt.where(Video.published_at >= utcnow() - timedelta(days=f.published_within_days))
        if f.has_transcript is True:
            stmt = stmt.where(Video.transcript_status == "ok")
        elif f.has_transcript is False:
            stmt = stmt.where(Video.transcript_status != "ok")
        return stmt

    def sorted(self, stmt: Select) -> Select:
        col = SORT_COLUMNS[self.sort]
        clause = col.asc() if self.order == "asc" else col.desc()
        return stmt.order_by(clause.nulls_last(), Video.video_id)


def to_trend_item(video: Video) -> TrendItem:
    item = TrendItem.model_validate(video)
    if video.discovered_keyword is not None:
        item.keyword = video.discovered_keyword.keyword
    return item


@router.get("/trends", response_model=TrendPage)
async def list_trends(
    filters: TrendFilters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    stmt = filters.apply(select(Video))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0

    stmt = (
        filters.sorted(stmt)
        .options(selectinload(Video.discovered_keyword))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    videos = (await db.execute(stmt)).scalars().all()
    pages = max(1, -(-total // page_size))
    return TrendPage(
        items=[to_trend_item(v) for v in videos], total=total, page=page, page_size=page_size, pages=pages
    )


@router.get("/trends/export.csv")
async def export_trends_csv(
    filters: TrendFilters = Depends(),
    db: AsyncSession = Depends(get_session),
):
    """Full filtered dataset (not just the visible page), Excel-friendly UTF-8 BOM."""
    stmt = (
        filters.sorted(filters.apply(select(Video)))
        .options(selectinload(Video.discovered_keyword))
        .limit(EXPORT_MAX_ROWS)
    )
    videos = (await db.execute(stmt)).scalars().all()

    header = [
        "video_id", "title", "channel", "url", "discovered_via_keyword", "published_at", "first_seen_at",
        "views", "likes", "comments", "like_ratio_pct", "view_velocity_per_hour", "like_velocity_per_hour",
        "positive_pct", "negative_pct", "neutral_pct", "avg_compound", "transcript_status", "thumbnail_url",
    ]

    def rows():
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\r\n")
        yield "﻿"  # BOM so Excel detects UTF-8
        writer.writerow(header)
        for v in videos:
            item = to_trend_item(v).model_dump(mode="json")
            writer.writerow([
                v.video_id, v.title, v.channel_title, v.url, item["keyword"] or "",
                item["published_at"] or "",
                item["first_seen_at"] or "",
                v.latest_view_count, v.latest_like_count, v.latest_comment_count,
                v.like_ratio if v.like_ratio is not None else "",
                v.view_velocity if v.view_velocity is not None else "",
                v.like_velocity if v.like_velocity is not None else "",
                v.sentiment_positive_pct if v.sentiment_positive_pct is not None else "",
                v.sentiment_negative_pct if v.sentiment_negative_pct is not None else "",
                v.sentiment_neutral_pct if v.sentiment_neutral_pct is not None else "",
                v.sentiment_compound if v.sentiment_compound is not None else "",
                v.transcript_status, v.thumbnail_url,
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    filename = f"pulsetube_trends_{utcnow().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        rows(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stats/overview", response_model=OverviewOut)
async def overview(db: AsyncSession = Depends(get_session)):
    day_ago = utcnow() - timedelta(hours=24)
    videos_total = (await db.execute(select(func.count()).select_from(Video))).scalar() or 0
    videos_new = (
        await db.execute(select(func.count()).select_from(Video).where(Video.first_seen_at >= day_ago))
    ).scalar() or 0
    total_views = (await db.execute(select(func.coalesce(func.sum(Video.latest_view_count), 0)))).scalar() or 0
    avg_positive = (
        await db.execute(
            select(func.avg(Video.sentiment_positive_pct)).where(Video.sentiment_positive_pct.isnot(None))
        )
    ).scalar()

    movers = (
        (
            await db.execute(
                select(Video)
                .where(Video.view_velocity.isnot(None), Video.view_velocity > 0)
                .options(selectinload(Video.discovered_keyword))
                .order_by(Video.view_velocity.desc())
                .limit(6)
            )
        )
        .scalars()
        .all()
    )
    return OverviewOut(
        videos_total=videos_total,
        videos_new_24h=videos_new,
        total_views_tracked=int(total_views),
        avg_positive_pct=round(avg_positive, 1) if avg_positive is not None else None,
        top_movers=[to_trend_item(v) for v in movers],
    )
