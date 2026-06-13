from fastapi import APIRouter

from . import keywords, system, trends, videos

api_router = APIRouter(prefix="/api")
api_router.include_router(trends.router, tags=["trends"])
api_router.include_router(videos.router, tags=["videos"])
api_router.include_router(keywords.router, tags=["keywords"])
api_router.include_router(system.router, tags=["system"])
