from datetime import datetime, timezone

from zoneinfo import ZoneInfo

# YouTube Data API quota resets at midnight *Pacific* time, so the daily
# ledger is keyed by the Pacific calendar date — not UTC.
PACIFIC = ZoneInfo("America/Los_Angeles")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def quota_day_today() -> str:
    return datetime.now(PACIFIC).strftime("%Y-%m-%d")


def ensure_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; everything we store is UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
