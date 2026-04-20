"""Research history — list + detail for the current user."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam, Response, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from db.models import Query, User
from services.auth import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"])


class HistorySummary(BaseModel):
    id: str
    query: str
    confidence: float | None
    iterations: int | None
    created_at: str


class HistoryDetail(HistorySummary):
    run_id: str | None = None
    final_answer: str | None = None
    duration_ms: float | None = None
    citations: list[dict[str, Any]] = []
    caveats: list[str] = []
    contradictions: list[dict[str, Any]] = []


@router.get("", response_model=list[HistorySummary])
async def list_history(
    limit: int = QueryParam(default=25, ge=1, le=100),
    offset: int = QueryParam(default=0, ge=0),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[HistorySummary]:
    stmt = (
        select(Query)
        .where(Query.user_id == current.id)
        .order_by(desc(Query.created_at))
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [HistorySummary(**row.to_summary()) for row in rows]


@router.get("/{query_id}", response_model=HistoryDetail)
async def get_history_item(
    query_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> HistoryDetail:
    stmt = select(Query).where(Query.id == query_id, Query.user_id == current.id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return HistoryDetail(**row.to_detail())


@router.delete("/{query_id}", response_model=None, status_code=204)
async def delete_history_item(
    query_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    stmt = select(Query).where(Query.id == query_id, Query.user_id == current.id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await db.delete(row)
    await db.commit()
    return Response(status_code=204)
