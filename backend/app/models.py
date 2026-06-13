from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .utils import utcnow


class TrackedKeyword(Base):
    """Global trend keywords plus user-defined product keywords (spec: tracked_keywords)."""

    __tablename__ = "tracked_keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="custom", nullable=False)  # global | custom
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_searched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    videos: Mapped[list["Video"]] = relationship(back_populates="discovered_keyword")

    __table_args__ = (Index("ux_tracked_keywords_keyword_lower", func.lower(keyword), unique=True),)


class Video(Base):
    """Video metadata + denormalized latest metrics (spec: videos_snapshot).

    The `latest_*` / velocity / sentiment columns are maintained by the
    pipeline (single writer) so dashboard filtering and sorting stay a
    cheap single-table query; full time series lives in
    video_metrics_history.
    """

    __tablename__ = "videos_snapshot"

    video_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    channel_id: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    channel_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    discovered_keyword_id: Mapped[int | None] = mapped_column(
        ForeignKey("tracked_keywords.id", ondelete="SET NULL"), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    latest_view_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    latest_like_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    latest_comment_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # views/hour and likes/hour between the two most recent captures
    view_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    like_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    like_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # likes / views * 100

    sentiment_positive_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_negative_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_neutral_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_compound: Mapped[float | None] = mapped_column(Float, nullable=True)

    transcript_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)

    discovered_keyword: Mapped[TrackedKeyword | None] = relationship(back_populates="videos")
    metrics: Mapped[list["MetricsSnapshot"]] = relationship(
        back_populates="video", cascade="all, delete-orphan", passive_deletes=True
    )
    transcript: Mapped["Transcript | None"] = relationship(
        back_populates="video", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    sentiment_runs: Mapped[list["SentimentAnalysis"]] = relationship(
        back_populates="video", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_videos_latest_view_count", "latest_view_count"),
        Index("ix_videos_published_at", "published_at"),
        Index("ix_videos_first_seen_at", "first_seen_at"),
    )

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


class MetricsSnapshot(Base):
    """Time-series of views/likes/comments per ingestion run (spec: video_metrics_history)."""

    __tablename__ = "video_metrics_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        ForeignKey("videos_snapshot.video_id", ondelete="CASCADE"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    view_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    video: Mapped[Video] = relationship(back_populates="metrics")

    __table_args__ = (Index("ix_metrics_video_captured", "video_id", "captured_at"),)


class Transcript(Base):
    """Full-text transcript per video (spec: transcripts)."""

    __tablename__ = "transcripts"

    video_id: Mapped[str] = mapped_column(
        ForeignKey("videos_snapshot.video_id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), default="ok", nullable=False)  # ok | unavailable | error
    language: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # provider name
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    video: Mapped[Video] = relationship(back_populates="transcript")


class SentimentAnalysis(Base):
    """Aggregate VADER scores over top comment threads (spec: sentiment_analytics)."""

    __tablename__ = "sentiment_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        ForeignKey("videos_snapshot.video_id", ondelete="CASCADE"), nullable=False
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    comments_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    positive_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    negative_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    neutral_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_compound: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Top comments with per-comment label, for the "what people are saying" panel
    sample_comments: Mapped[list | None] = mapped_column(JSON, nullable=True)

    video: Mapped[Video] = relationship(back_populates="sentiment_runs")

    __table_args__ = (Index("ix_sentiment_video_computed", "video_id", "computed_at"),)


class PipelineRun(Base):
    """Operational log of each ingestion cycle — powers the System page and quota handling."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    # running | success | partial | failed | halted_quota
    trigger: Mapped[str] = mapped_column(String(16), default="scheduled", nullable=False)
    keywords_searched: Mapped[list | None] = mapped_column(JSON, nullable=True)
    videos_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    videos_refreshed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transcripts_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sentiment_computed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota_units_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class QuotaUsage(Base):
    """Daily YouTube API unit ledger, keyed by Pacific-time date (quota reset boundary)."""

    __tablename__ = "quota_usage"

    quota_date: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD (America/Los_Angeles)
    units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
