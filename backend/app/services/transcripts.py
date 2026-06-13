"""Transcript ingestion behind a pluggable provider interface.

Default provider is the free `youtube-transcript-api` library (zero cost,
no YouTube quota). When volume or IP-blocking demands it, switch to the
paid Supadata HTTP API by setting TRANSCRIPT_PROVIDER=supadata — no code
changes required.
"""

import asyncio
import re
from dataclasses import dataclass

import httpx

from ..config import get_settings

# Cue markers like [Music] add noise to the stored script
_CUE_RE = re.compile(r"\[(?:music|applause|laughter|cheering)\]", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")

FETCH_TIMEOUT_SECONDS = 60
PREFERRED_LANGUAGES = ["en", "en-US", "en-GB"]


@dataclass
class TranscriptResult:
    status: str  # ok | unavailable | error
    language: str = ""
    source: str = ""
    text: str = ""

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text else 0


def _clean(text: str) -> str:
    return _WS_RE.sub(" ", _CUE_RE.sub(" ", text)).strip()


class YouTubeTranscriptApiProvider:
    """Free library provider — scrapes YouTube's own caption tracks."""

    name = "youtube-transcript-api"

    def _fetch_sync(self, video_id: str) -> TranscriptResult:
        from youtube_transcript_api import (
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
            YouTubeTranscriptApi,
        )
        from youtube_transcript_api._errors import CouldNotRetrieveTranscript

        api = YouTubeTranscriptApi()
        try:
            try:
                fetched = api.fetch(video_id, languages=PREFERRED_LANGUAGES)
            except NoTranscriptFound:
                # No English track — take whatever language exists.
                transcript_list = api.list(video_id)
                first = next(iter(transcript_list))
                fetched = first.fetch()
            text = _clean(" ".join(snippet.text for snippet in fetched))
            if not text:
                return TranscriptResult(status="unavailable", source=self.name)
            return TranscriptResult(
                status="ok",
                language=getattr(fetched, "language_code", "") or "",
                source=self.name,
                text=text,
            )
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, StopIteration):
            return TranscriptResult(status="unavailable", source=self.name)
        except CouldNotRetrieveTranscript:
            # Includes IP blocks / rate limits — retryable later or via paid provider
            return TranscriptResult(status="error", source=self.name)

    async def fetch(self, video_id: str) -> TranscriptResult:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._fetch_sync, video_id), timeout=FETCH_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            return TranscriptResult(status="error", source=self.name)
        except Exception:
            return TranscriptResult(status="error", source=self.name)


class SupadataProvider:
    """Paid HTTP provider (~$30/mo tier) — survives IP rate-limits at scale."""

    name = "supadata"

    async def fetch(self, video_id: str) -> TranscriptResult:
        settings = get_settings()
        if not settings.supadata_api_key:
            return TranscriptResult(status="error", source=self.name)
        try:
            async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_SECONDS) as client:
                resp = await client.get(
                    settings.supadata_api_url,
                    params={"videoId": video_id, "text": "true"},
                    headers={"x-api-key": settings.supadata_api_key},
                )
            if resp.status_code == 200:
                data = resp.json()
                text = _clean(str(data.get("content") or data.get("text") or ""))
                if not text:
                    return TranscriptResult(status="unavailable", source=self.name)
                return TranscriptResult(
                    status="ok", language=str(data.get("lang", "")), source=self.name, text=text
                )
            if resp.status_code == 404:
                return TranscriptResult(status="unavailable", source=self.name)
            return TranscriptResult(status="error", source=self.name)
        except httpx.HTTPError:
            return TranscriptResult(status="error", source=self.name)


def get_transcript_provider():
    if get_settings().transcript_provider.lower() == "supadata":
        return SupadataProvider()
    return YouTubeTranscriptApiProvider()
