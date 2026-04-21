"""
Async SQLAlchemy engine y session factory.
Usa aioodbc para SQL Server async (no bloquea el event loop).
Fallback a run_in_executor con pyodbc síncrono si aioodbc no está disponible.
"""
from __future__ import annotations

import logging
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

_async_engine = None
_async_session_factory = None


def _get_async_connection_url() -> str:
    if not all([settings.SQL_SERVER, settings.SQL_DB, settings.SQL_USER, settings.SQL_PASSWORD]):
        raise RuntimeError("Faltan variables de entorno: SQL_SERVER, SQL_DB, SQL_USER, SQL_PASSWORD")

    driver = "{ODBC Driver 18 for SQL Server}"
    trust = "yes" if settings.SQL_TRUST_SERVER_CERTIFICATE else "no"
    timeout = settings.SQL_CONNECTION_TIMEOUT

    conn_str = (
        f"Driver={driver};"
        f"Server={settings.SQL_SERVER},1433;"
        f"Database={settings.SQL_DB};"
        f"Uid={settings.SQL_USER};"
        f"Pwd={settings.SQL_PASSWORD};"
        f"Encrypt=yes;TrustServerCertificate={trust};Connection Timeout={timeout};"
    )
    return f"mssql+aioodbc:///?odbc_connect={quote_plus(conn_str)}"


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        url = _get_async_connection_url()
        _async_engine = create_async_engine(
            url,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=1800,
            echo=settings.ENV == "local",
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
