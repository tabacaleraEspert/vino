"""Conexión a Azure SQL Database."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import pyodbc

from app.core.config import settings
from app.core.request_metrics import time_sql_block


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


@contextmanager
def get_connection() -> Generator[pyodbc.Connection, None, None]:
    """Context manager para obtener conexión a Azure SQL."""
    with time_sql_block():
        conn = pyodbc.connect(_get_connection_string())
        try:
            yield conn
        finally:
            conn.close()
