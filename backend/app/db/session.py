"""
Async SQLAlchemy engine y session factory.
Usa asyncpg para PostgreSQL (Neon).
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

_async_engine = None
_async_session_factory = None


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        url = settings.DATABASE_URL
        if not url:
            raise RuntimeError("Falta variable de entorno: DATABASE_URL")
        # Neon requires ssl=require; asyncpg uses ssl keyword
        if "sslmode=require" in url:
            url = url.replace("sslmode=require", "ssl=require")
        _async_engine = create_async_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,
            echo=False,
        )
    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async session, auto-commits or rolls back."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
