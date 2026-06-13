"""Tracked keyword management — the spec's custom tracking interface."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import TrackedKeyword, Video
from ..schemas import KeywordCreate, KeywordOut, KeywordPatch

router = APIRouter()


@router.get("/keywords", response_model=list[KeywordOut])
async def list_keywords(db: AsyncSession = Depends(get_session)):
    counts = dict(
        (
            await db.execute(
                select(Video.discovered_keyword_id, func.count())
                .where(Video.discovered_keyword_id.isnot(None))
                .group_by(Video.discovered_keyword_id)
            )
        ).all()
    )
    keywords = (
        (await db.execute(select(TrackedKeyword).order_by(TrackedKeyword.kind, TrackedKeyword.keyword)))
        .scalars()
        .all()
    )
    out = []
    for kw in keywords:
        item = KeywordOut.model_validate(kw)
        item.video_count = counts.get(kw.id, 0)
        out.append(item)
    return out


@router.post("/keywords", response_model=KeywordOut, status_code=201)
async def create_keyword(payload: KeywordCreate, db: AsyncSession = Depends(get_session)):
    keyword = " ".join(payload.keyword.split())  # collapse stray whitespace
    if len(keyword) < 2:
        raise HTTPException(status_code=422, detail="Keyword is too short")
    duplicate = (
        await db.execute(
            select(TrackedKeyword).where(func.lower(TrackedKeyword.keyword) == keyword.lower())
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail=f'"{duplicate.keyword}" is already tracked')

    kw = TrackedKeyword(keyword=keyword, kind="custom", is_active=True)
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    # Newly added keywords sort first for the next cycle (last_searched_at is NULL)
    return KeywordOut.model_validate(kw)


@router.patch("/keywords/{keyword_id}", response_model=KeywordOut)
async def update_keyword(keyword_id: int, payload: KeywordPatch, db: AsyncSession = Depends(get_session)):
    kw = await db.get(TrackedKeyword, keyword_id)
    if kw is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    if payload.is_active is not None:
        kw.is_active = payload.is_active
    await db.commit()
    await db.refresh(kw)
    return KeywordOut.model_validate(kw)


@router.delete("/keywords/{keyword_id}", status_code=204)
async def delete_keyword(keyword_id: int, db: AsyncSession = Depends(get_session)):
    kw = await db.get(TrackedKeyword, keyword_id)
    if kw is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    if kw.kind == "global":
        raise HTTPException(status_code=400, detail="Global trend keywords can be deactivated, not deleted")
    await db.delete(kw)  # discovered videos keep tracking (FK SET NULL)
    await db.commit()
