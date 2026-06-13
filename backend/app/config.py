from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    youtube_api_key: str = ""
    database_url: str = ""

    pipeline_interval_minutes: int = 120
    run_pipeline_on_startup: bool = False

    search_keywords_per_run: int = 3
    search_max_results: int = 25
    search_published_within_days: int = 7
    search_order: str = "viewCount"
    region_code: str = "US"
    relevance_language: str = "en"

    daily_quota_limit: int = 10_000
    quota_safety_buffer: int = 500

    metrics_refresh_window_days: int = 14
    comments_max_per_video: int = 100

    transcript_provider: str = "youtube-transcript-api"
    supadata_api_key: str = ""
    supadata_api_url: str = "https://api.supadata.ai/v1/youtube/transcript"
    transcript_concurrency: int = 3

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def effective_database_url(self) -> str:
        return self.database_url or "sqlite+aiosqlite:///./pulsetube.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def quota_budget(self) -> int:
        return self.daily_quota_limit - self.quota_safety_buffer


@lru_cache
def get_settings() -> Settings:
    return Settings()
