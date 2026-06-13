"""PulseTube backend — FastAPI app + in-process ingestion scheduler.

Run from the backend/ directory:  python -m uvicorn app.main:app --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from .api import api_router
from .config import get_settings
from .database import engine, init_db, session_scope
from .models import TrackedKeyword
from .workers.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("pulsetube")

# Spec's high-velocity trend keywords, seeded once on first boot
DEFAULT_GLOBAL_KEYWORDS = [
    "top trending products",
    "amazon finds",
    "tiktok made me buy it",
    "unboxing",
    "product review",
]


async def ensure_default_keywords() -> None:
    async with session_scope() as db:
        count = (await db.execute(select(func.count()).select_from(TrackedKeyword))).scalar() or 0
        if count == 0:
            for kw in DEFAULT_GLOBAL_KEYWORDS:
                db.add(TrackedKeyword(keyword=kw, kind="global"))
            await db.commit()
            logger.info("seeded %d default global keywords", len(DEFAULT_GLOBAL_KEYWORDS))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_default_keywords()
    start_scheduler()
    if not get_settings().youtube_api_key:
        logger.warning("YOUTUBE_API_KEY is empty — pipeline runs will fail until it is set in backend/.env")
    yield
    shutdown_scheduler()
    await engine.dispose()


app = FastAPI(
    title="PulseTube API",
    description="Automated YouTube product trend analytics: discovery, metrics velocity, sentiment, transcripts.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "pulsetube", "version": app.version}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Last-resort guard: log the traceback, never leak internals to the client
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
