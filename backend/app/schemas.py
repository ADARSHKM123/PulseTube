from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from .utils import ensure_utc


def _iso_z(dt: datetime | None) -> str | None:
    dt = ensure_utc(dt)
    return dt.isoformat().replace("+00:00", "Z") if dt else None


# SQLite hands back naive datetimes; serialize everything as explicit UTC.
UTCStamp = Annotated[datetime | None, PlainSerializer(_iso_z, return_type=str | None, when_used="json")]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Keywords ─────────────────────────────────────────────────────────────────
class KeywordOut(ORMModel):
    id: int
    keyword: str
    kind: str
    is_active: bool
    created_at: UTCStamp = None
    last_searched_at: UTCStamp = None
    search_count: int
    video_count: int = 0


class KeywordCreate(BaseModel):
    keyword: str = Field(min_length=2, max_length=255)


class KeywordPatch(BaseModel):
    is_active: bool | None = None


# ── Trends / videos ──────────────────────────────────────────────────────────
class TrendItem(ORMModel):
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    url: str
    thumbnail_url: str
    duration_seconds: int | None = None
    published_at: UTCStamp = None
    first_seen_at: UTCStamp = None
    last_refreshed_at: UTCStamp = None
    latest_view_count: int
    latest_like_count: int
    latest_comment_count: int
    view_velocity: float | None = None
    like_velocity: float | None = None
    like_ratio: float | None = None
    sentiment_positive_pct: float | None = None
    sentiment_negative_pct: float | None = None
    sentiment_neutral_pct: float | None = None
    sentiment_compound: float | None = None
    transcript_status: str
    keyword: str | None = None


class TrendPage(BaseModel):
    items: list[TrendItem]
    total: int
    page: int
    page_size: int
    pages: int


class SentimentOut(ORMModel):
    computed_at: UTCStamp = None
    comments_analyzed: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    avg_compound: float
    sample_comments: list[dict[str, Any]] | None = None


class VideoDetail(TrendItem):
    description: str = ""
    tags: list[str] | None = None
    sentiment: SentimentOut | None = None


class MetricsPoint(ORMModel):
    captured_at: UTCStamp = None
    view_count: int
    like_count: int
    comment_count: int


class TranscriptOut(BaseModel):
    video_id: str
    status: str
    language: str = ""
    source: str = ""
    content: str = ""
    word_count: int = 0
    fetched_at: UTCStamp = None


# ── System / pipeline ────────────────────────────────────────────────────────
class RunOut(ORMModel):
    id: int
    started_at: UTCStamp = None
    finished_at: UTCStamp = None
    status: str
    trigger: str
    keywords_searched: list[str] | None = None
    videos_discovered: int
    videos_refreshed: int
    comments_fetched: int
    transcripts_fetched: int
    sentiment_computed: int
    quota_units_used: int
    error: str | None = None


class QuotaOut(BaseModel):
    date: str
    used: int
    limit: int
    budget: int
    remaining: int


class TotalsOut(BaseModel):
    videos: int
    active_keywords: int
    transcripts_ok: int
    with_sentiment: int


class ConfigOut(BaseModel):
    interval_minutes: int
    keywords_per_run: int
    search_order: str
    region_code: str
    published_within_days: int
    transcript_provider: str
    api_key_configured: bool


class StatusOut(BaseModel):
    pipeline_running: bool
    last_run: RunOut | None = None
    next_run_at: UTCStamp = None
    quota: QuotaOut
    totals: TotalsOut
    config: ConfigOut


class OverviewOut(BaseModel):
    videos_total: int
    videos_new_24h: int
    total_views_tracked: int
    avg_positive_pct: float | None = None
    top_movers: list[TrendItem]
