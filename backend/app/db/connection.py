"""Conexión a Azure SQL Database con pool de conexiones."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from urllib.parse import quote_plus
from typing import Generator

import pyodbc

from app.core.config import settings
from app.core.request_metrics import add_sql_time

logger = logging.getLogger(__name__)

_engine = None


def _get_connection_string() -> str:
    if not all([settings.SQL_SERVER, settings.SQL_DB, settings.SQL_USER, settings.SQL_PASSWORD]):
        raise RuntimeError(
            "Faltan variables de entorno: SQL_SERVER, SQL_DB, SQL_USER, SQL_PASSWORD"
        )
    driver = "{ODBC Driver 18 for SQL Server}"
    return (
        f"Driver={driver};"
        f"Server={settings.SQL_SERVER},1433;"
        f"Database={settings.SQL_DB};"
        f"Uid={settings.SQL_USER};"
        f"Pwd={settings.SQL_PASSWORD};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )


def _get_engine():
    """Engine con pool (lazy init)."""
    global _engine
    if _engine is None:
        try:
            from sqlalchemy import create_engine

            conn_str = _get_connection_string()
            url = f"mssql+pyodbc:///?odbc_connect={quote_plus(conn_str)}"
            _engine = create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=1800,
            )
        except Exception as e:
            logger.warning("SQLAlchemy no disponible, usando pyodbc directo: %s", e)
            _engine = None
    return _engine


@contextmanager
def get_connection() -> Generator[pyodbc.Connection, None, None]:
    """
    Context manager para obtener conexión a Azure SQL.
    Reusa pool cuando SQLAlchemy está disponible.
    """
    t0 = time.perf_counter()
    try:
        engine = _get_engine()
        if engine:
            with engine.connect() as conn:
                raw = conn.connection
                yield raw
        else:
            conn = pyodbc.connect(_get_connection_string())
            try:
                yield conn
            finally:
                conn.close()
    finally:
        add_sql_time(time.perf_counter() - t0)
