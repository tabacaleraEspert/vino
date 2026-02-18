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
