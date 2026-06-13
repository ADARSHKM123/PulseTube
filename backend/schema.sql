-- ============================================================================
-- PulseTube — PostgreSQL initialization DDL
-- ============================================================================
-- The FastAPI app also creates this schema automatically at boot
-- (SQLAlchemy metadata.create_all), so this file is for provisioning a
-- managed PostgreSQL instance directly or reviewing the relational design.
-- ============================================================================

BEGIN;

-- Global trend keywords + user-defined product keywords
CREATE TABLE IF NOT EXISTS tracked_keywords (
    id                  SERIAL PRIMARY KEY,
    keyword             VARCHAR(255) NOT NULL,
    kind                VARCHAR(16)  NOT NULL DEFAULT 'custom',   -- global | custom
    is_active           BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_searched_at    TIMESTAMPTZ,
    search_count        INTEGER      NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_tracked_keywords_keyword_lower
    ON tracked_keywords (lower(keyword));

-- Video metadata + denormalized latest metrics (single writer: the pipeline).
-- Latest-value columns keep dashboard filtering/sorting a one-table scan;
-- the authoritative time series lives in video_metrics_history.
CREATE TABLE IF NOT EXISTS videos_snapshot (
    video_id                VARCHAR(20)  PRIMARY KEY,             -- YouTube video id
    title                   TEXT         NOT NULL,
    description             TEXT         NOT NULL DEFAULT '',
    channel_id              VARCHAR(40)  NOT NULL DEFAULT '',
    channel_title           VARCHAR(255) NOT NULL DEFAULT '',
    published_at            TIMESTAMPTZ,
    thumbnail_url           TEXT         NOT NULL DEFAULT '',
    duration_seconds        INTEGER,
    tags                    JSONB,
    discovered_keyword_id   INTEGER REFERENCES tracked_keywords(id) ON DELETE SET NULL,
    first_seen_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_refreshed_at       TIMESTAMPTZ,
    latest_view_count       BIGINT       NOT NULL DEFAULT 0,
    latest_like_count       BIGINT       NOT NULL DEFAULT 0,
    latest_comment_count    BIGINT       NOT NULL DEFAULT 0,
    view_velocity           DOUBLE PRECISION,                     -- views/hour between last two captures
    like_velocity           DOUBLE PRECISION,
    like_ratio              DOUBLE PRECISION,                     -- likes / views * 100
    sentiment_positive_pct  DOUBLE PRECISION,
    sentiment_negative_pct  DOUBLE PRECISION,
    sentiment_neutral_pct   DOUBLE PRECISION,
    sentiment_compound      DOUBLE PRECISION,
    transcript_status       VARCHAR(16)  NOT NULL DEFAULT 'pending'  -- pending | ok | unavailable | error
);
CREATE INDEX IF NOT EXISTS ix_videos_latest_view_count ON videos_snapshot (latest_view_count);
CREATE INDEX IF NOT EXISTS ix_videos_published_at      ON videos_snapshot (published_at);
CREATE INDEX IF NOT EXISTS ix_videos_first_seen_at     ON videos_snapshot (first_seen_at);

-- Time-series metrics captured on each of the 8–12 daily runs
CREATE TABLE IF NOT EXISTS video_metrics_history (
    id              BIGSERIAL    PRIMARY KEY,
    video_id        VARCHAR(20)  NOT NULL REFERENCES videos_snapshot(video_id) ON DELETE CASCADE,
    captured_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    view_count      BIGINT       NOT NULL DEFAULT 0,
    like_count      BIGINT       NOT NULL DEFAULT 0,
    comment_count   BIGINT       NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_metrics_video_captured
    ON video_metrics_history (video_id, captured_at);

-- Full-text transcripts (one per video, provider-agnostic)
CREATE TABLE IF NOT EXISTS transcripts (
    video_id    VARCHAR(20) PRIMARY KEY REFERENCES videos_snapshot(video_id) ON DELETE CASCADE,
    status      VARCHAR(16) NOT NULL DEFAULT 'ok',                -- ok | unavailable | error
    language    VARCHAR(16) NOT NULL DEFAULT '',
    source      VARCHAR(32) NOT NULL DEFAULT '',                  -- youtube-transcript-api | supadata
    content     TEXT        NOT NULL DEFAULT '',
    word_count  INTEGER     NOT NULL DEFAULT 0,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Aggregate VADER sentiment per computation (history preserved)
CREATE TABLE IF NOT EXISTS sentiment_analytics (
    id                  SERIAL       PRIMARY KEY,
    video_id            VARCHAR(20)  NOT NULL REFERENCES videos_snapshot(video_id) ON DELETE CASCADE,
    computed_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    comments_analyzed   INTEGER      NOT NULL DEFAULT 0,
    positive_pct        DOUBLE PRECISION NOT NULL DEFAULT 0,
    negative_pct        DOUBLE PRECISION NOT NULL DEFAULT 0,
    neutral_pct         DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_compound        DOUBLE PRECISION NOT NULL DEFAULT 0,
    sample_comments     JSONB                                     -- top comments w/ per-comment label
);
CREATE INDEX IF NOT EXISTS ix_sentiment_video_computed
    ON sentiment_analytics (video_id, computed_at);

-- Operational log of ingestion cycles (status page, quota accounting)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id                   SERIAL      PRIMARY KEY,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at          TIMESTAMPTZ,
    status               VARCHAR(16) NOT NULL DEFAULT 'running',  -- running | success | partial | failed | halted_quota
    trigger              VARCHAR(16) NOT NULL DEFAULT 'scheduled',-- scheduled | manual
    keywords_searched    JSONB,
    videos_discovered    INTEGER     NOT NULL DEFAULT 0,
    videos_refreshed     INTEGER     NOT NULL DEFAULT 0,
    comments_fetched     INTEGER     NOT NULL DEFAULT 0,
    transcripts_fetched  INTEGER     NOT NULL DEFAULT 0,
    sentiment_computed   INTEGER     NOT NULL DEFAULT 0,
    quota_units_used     INTEGER     NOT NULL DEFAULT 0,
    error                TEXT
);

-- Daily YouTube API unit ledger, keyed by *Pacific* date (Google's reset boundary)
CREATE TABLE IF NOT EXISTS quota_usage (
    quota_date  VARCHAR(10) PRIMARY KEY,                          -- YYYY-MM-DD America/Los_Angeles
    units       INTEGER     NOT NULL DEFAULT 0
);

COMMIT;
