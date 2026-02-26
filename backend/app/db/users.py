"""Acceso a usuarios en Azure SQL."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

from app.db.connection import get_connection
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache: nombre -> (user_dict, timestamp)
_login_cache: Dict[str, tuple] = {}
_login_cache_lock = threading.Lock()


def get_user_by_nombre(nombre: str) -> Optional[Dict[str, Any]]:
    """
    Busca usuario por Nombre (usado en login).
    Query minimalista: solo id, Nombre, Apellido, ID_Sheets, PasswordHash.
    Cache opcional 60s para reducir latencia en logins repetidos.
    """
    nombre_norm = nombre.strip()
    ttl = settings.SQL_LOGIN_CACHE_TTL_SEC

    if ttl > 0:
        with _login_cache_lock:
            entry = _login_cache.get(nombre_norm)
            if entry:
                user, ts = entry
                if time.time() - ts <= ttl:
                    logger.info("sql_login_cache_hit=true nombre=%s", nombre_norm)
                    return user
                _login_cache.pop(nombre_norm, None)

    table = settings.SQL_USUARIO_TABLE
    t0 = time.perf_counter()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, Nombre, Apellido, ID_Sheets, PasswordHash, gmail FROM [{table}] WHERE Nombre = ?",
            (nombre_norm,),
        )
        row = cursor.fetchone()
    t_ms = (time.perf_counter() - t0) * 1000
    logger.info("sql_query_ms=%.0f rows_returned=%d", t_ms, 1 if row else 0)

    if not row:
        return None

    cols = ["id", "Nombre", "Apellido", "ID_Sheets", "PasswordHash", "gmail"]
    user = dict(zip(cols, (str(x) if x is not None else "" for x in row)))

    if ttl > 0:
        with _login_cache_lock:
            _login_cache[nombre_norm] = (user, time.time())

    return user


def create_user(
    nombre: str,
    password_hash: str,
    apellido: Optional[str] = None,
    gmail: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crea usuario en MaestroUsuarios.
    ID_Sheets queda NULL (usuario SQL-only; puede asignarse después).
    Retorna el usuario creado.
    """
    nombre_norm = nombre.strip()
    if not nombre_norm:
        raise ValueError("Nombre es requerido")
    if not password_hash:
        raise ValueError("PasswordHash es requerido")

    if get_user_by_nombre(nombre_norm):
        raise ValueError("Ya existe un usuario con ese nombre")

    table = settings.SQL_USUARIO_TABLE
    params = (nombre_norm, (apellido or "").strip() or None, (gmail or "").strip() or None, password_hash)
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                INSERT INTO [{table}] (Nombre, Apellido, gmail, PasswordHash, ID_Sheets)
                OUTPUT INSERTED.Id, INSERTED.Nombre, INSERTED.Apellido, INSERTED.gmail, INSERTED.ID_Sheets, INSERTED.PasswordHash
                VALUES (?, ?, ?, ?, NULL)
                """,
                params,
            )
        except Exception as e:
            err_msg = str(e).lower()
            # Tabla sin IDENTITY en id: generar id explícitamente
            if "null" in err_msg and "id" in err_msg:
                cursor.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM [{table}]")
                next_id = cursor.fetchone()[0]
                cursor.execute(
                    f"""
                    INSERT INTO [{table}] (id, Nombre, Apellido, gmail, PasswordHash, ID_Sheets)
                    OUTPUT INSERTED.Id, INSERTED.Nombre, INSERTED.Apellido, INSERTED.gmail, INSERTED.ID_Sheets, INSERTED.PasswordHash
                    VALUES (?, ?, ?, ?, ?, NULL)
                    """,
                    (next_id,) + params,
                )
            else:
                raise
        row = cursor.fetchone()
        conn.commit()

    if not row:
        raise RuntimeError("No se pudo crear el usuario")

    return {
        "id": str(row[0]),
        "Nombre": str(row[1] or ""),
        "Apellido": str(row[2] or "") if row[2] else "",
        "gmail": str(row[3] or "") if row[3] else "",
        "ID_Sheets": str(row[4] or "") if row[4] else "",
        "PasswordHash": row[5],
    }
