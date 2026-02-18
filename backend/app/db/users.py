"""Acceso a usuarios en Azure SQL."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.db.connection import get_connection
from app.core.config import settings


def get_user_by_nombre(nombre: str) -> Optional[Dict[str, Any]]:
    """
    Busca usuario por Nombre (usado en login).
    Retorna dict con id, Nombre, Apellido, ID_Sheets, PasswordHash, etc.
    """
    table = settings.SQL_USUARIO_TABLE
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, Nombre, Apellido, WppEntero, Whatsapp, gmail, ID_Sheets, "
            f"PasswordHash, CreatedAt, UpdatedAt FROM [{table}] WHERE Nombre = ?",
            (nombre.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [
            "id", "Nombre", "Apellido", "WppEntero", "Whatsapp", "gmail",
            "ID_Sheets", "PasswordHash", "CreatedAt", "UpdatedAt",
        ]
        return dict(zip(cols, (str(x) if x is not None else "" for x in row)))
