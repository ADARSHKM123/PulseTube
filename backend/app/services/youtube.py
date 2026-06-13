"""Async YouTube Data API v3 client with a persistent daily quota ledger.

Unit costs (official quota calculator):
  search.list          = 100 units
  videos.list          = 1 unit   (regardless of id count, batched up to 50)
  commentThreads.list  = 1 unit
"""

import asyncio
import re
from datetime import timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import QuotaUsage
from ..utils import quota_day_today, utcnow

API_BASE = "https://www.googleapis.com/youtube/v3"

COST_SEARCH = 100
COST_VIDEOS_LIST = 1
COST_COMMENT_THREADS = 1

_DURATION_RE = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


class YouTubeAPIError(Exception):
    """Generic upstream API failure."""


class QuotaExceededError(YouTubeAPIError):
    """Google rejected the call: the project's daily quota is spent."""


class QuotaBudgetExhausted(YouTubeAPIError):
    """Our own safety budget (limit - buffer) is spent; stop calling for today."""


class CommentsDisabledError(YouTubeAPIError):
    """Comments are turned off for this video."""


def parse_iso8601_duration(value: str | None) -> int | None:
    if not value:
        return None
    m = _DURATION_RE.fullmatch(value)
    if not m:
        return None
    days, hours, minutes, seconds = (int(g) if g else 0 for g in m.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def pick_best_thumbnail(thumbnails: dict | None) -> str:
    if not thumbnails:
        return ""
    for key in ("maxres", "standard", "high", "medium", "default"):
        if key in thumbnails and thumbnails[key].get("url"):
            return thumbnails[key]["url"]
    return ""


async def quota_used_today(db: AsyncSession) -> int:
    row = await db.get(QuotaUsage, quota_day_today())
    return row.units if row else 0


async def reserve_quota(db: AsyncSession, units: int) -> None:
    """Record `units` against today's ledger, refusing if the budget would be blown.

    Reserved before the HTTP call — Google counts failed requests against
    quota too, so being pessimistic here keeps the ledger honest.
    """
    settings = get_settings()
    today = quota_day_today()
    row = await db.get(QuotaUsage, today)
    if row is None:
        row = QuotaUsage(quota_date=today, units=0)
        db.add(row)
    if row.units + units > settings.quota_budget:
        raise QuotaBudgetExhausted(
            f"Daily quota budget reached ({row.units}/{settings.quota_budget} units used); "
            "resuming after the Pacific-midnight reset."
        )
    row.units += units
    await db.commit()


class YouTubeClient:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.http = httpx.AsyncClient(timeout=30.0)
        self.units_used = 0

    async def close(self) -> None:
        await self.http.aclose()

    async def _get(self, endpoint: str, params: dict, cost: int) -> dict:
        if not self.settings.youtube_api_key:
            raise YouTubeAPIError("YOUTUBE_API_KEY is not configured (backend/.env)")
        await reserve_quota(self.db, cost)
        self.units_used += cost

        params = {**params, "key": self.settings.youtube_api_key}
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                resp = await self.http.get(f"{API_BASE}/{endpoint}", params=params)
            except httpx.TransportError as exc:
                last_exc = exc
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            if resp.status_code >= 500:
                last_exc = YouTubeAPIError(f"{endpoint}: upstream {resp.status_code}")
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            return self._handle_response(endpoint, resp)
        raise YouTubeAPIError(f"{endpoint}: request failed after retries ({last_exc})")

    def _handle_response(self, endpoint: str, resp: httpx.Response) -> dict:
        if resp.status_code == 200:
            return resp.json()
        try:
            error = resp.json().get("error", {})
            reasons = {e.get("reason", "") for e in error.get("errors", [])}
            message = error.get("message", resp.text[:300])
        except Exception:
            reasons, message = set(), resp.text[:300]
        if reasons & {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}:
            raise QuotaExceededError(f"{endpoint}: {message}")
        if "commentsDisabled" in reasons:
            raise CommentsDisabledError(message)
        raise YouTubeAPIError(f"{endpoint}: HTTP {resp.status_code} — {message}")

    async def search_videos(self, keyword: str) -> list[str]:
        """search.list with part=id — snippet/statistics come from the cheaper
        batched videos.list afterwards, so the expensive call stays minimal."""
        published_after = (utcnow() - timedelta(days=self.settings.search_published_within_days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        params = {
            "part": "id",
            "q": keyword,
            "type": "video",
            "order": self.settings.search_order,
            "publishedAfter": published_after,
            "maxResults": min(50, self.settings.search_max_results),
            "regionCode": self.settings.region_code,
            "relevanceLanguage": self.settings.relevance_language,
        }
        data = await self._get("search", params, COST_SEARCH)
        return [item["id"]["videoId"] for item in data.get("items", []) if item.get("id", {}).get("videoId")]

    async def list_videos(self, video_ids: list[str]) -> list[dict]:
        """Batched metadata + statistics lookup, 50 ids per unit."""
        items: list[dict] = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            params = {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(chunk),
                "maxResults": 50,
            }
            data = await self._get("videos", params, COST_VIDEOS_LIST)
            items.extend(data.get("items", []))
        return items

    async def list_comment_threads(self, video_id: str, max_results: int) -> list[dict]:
        """Top comment threads by relevance; one page (1 unit) feeds sentiment."""
        params = {
            "part": "snippet",
            "videoId": video_id,
            "order": "relevance",
            "maxResults": min(100, max_results),
            "textFormat": "plainText",
        }
        try:
            data = await self._get("commentThreads", params, COST_COMMENT_THREADS)
        except CommentsDisabledError:
            return []
        comments = []
        for item in data.get("items", []):
            top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            text = (top.get("textOriginal") or top.get("textDisplay") or "").strip()
            if not text:
                continue
            comments.append(
                {
                    "author": top.get("authorDisplayName", ""),
                    "text": text,
                    "like_count": int(top.get("likeCount", 0) or 0),
                    "published_at": top.get("publishedAt", ""),
                    "reply_count": int(item.get("snippet", {}).get("totalReplyCount", 0) or 0),
                }
            )
        return comments
