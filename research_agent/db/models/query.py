from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Use JSONB on Postgres, plain JSON on SQLite.
JsonCol = JSON().with_variant(JSONB(), "postgresql")


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    iterations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        MutableList.as_mutable(JsonCol), default=list, nullable=False
    )
    caveats: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JsonCol), default=list, nullable=False
    )
    contradictions: Mapped[list[dict[str, Any]]] = mapped_column(
        MutableList.as_mutable(JsonCol), default=list, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True, nullable=False
    )

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "query": self.query,
            "confidence": self.confidence,
            "iterations": self.iterations,
            "created_at": self.created_at.isoformat(),
        }

    def to_detail(self) -> dict:
        return {
            **self.to_summary(),
            "run_id": self.run_id,
            "final_answer": self.final_answer,
            "duration_ms": self.duration_ms,
            "citations": self.citations,
            "caveats": self.caveats,
            "contradictions": self.contradictions,
        }
