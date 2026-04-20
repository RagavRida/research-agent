"""Async SQLAlchemy engine + session factory.

DATABASE_URL formats:
  sqlite+aiosqlite:///./aria.db           (default, local dev)
  postgresql+asyncpg://user:pw@host/db    (production)
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields a DB session per request."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables if they don't exist. Called once at startup."""
    from .models import user  # noqa: F401  register models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
