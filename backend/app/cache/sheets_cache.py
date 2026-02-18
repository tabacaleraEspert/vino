"""
Cache in-memory para lecturas de Google Sheets por tabla.
TTL configurable.
Thread-safe con lock por tabla para evitar thundering herd.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache: (spreadsheet_id, table_name) -> (ts, (headers, rows))
_CacheValue = Tuple[float, Tuple[List[str], List[Dict[str, Any]]]]
_cache: Dict[tuple, _CacheValue] = {}
_cache_lock = threading.Lock()
# Per-table locks: (spreadsheet_id, table_name) -> threading.Lock
_table_locks: Dict[tuple, threading.Lock] = {}
_table_locks_lock = threading.Lock()


def _get_table_lock(spreadsheet_id: str, table_name: str) -> threading.Lock:
    key = (spreadsheet_id, table_name)
    with _table_locks_lock:
        if key not in _table_locks:
            _table_locks[key] = threading.Lock()
        return _table_locks[key]


def get_table(
    spreadsheet_id: str,
    table_name: str,
    fetch_fn: Callable[[], Tuple[List[str], List[Dict[str, Any]]]],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Obtiene datos de tabla desde cache o ejecuta fetch_fn.
    Thread-safe: evita thundering herd con lock por tabla.
    """
    ttl = settings.SHEETS_CACHE_TTL_SEC
    key = (spreadsheet_id, table_name)

    if ttl <= 0:
        return fetch_fn()

    # Lectura rápida bajo lock global
    with _cache_lock:
        entry = _cache.get(key)
        if entry:
            ts, (headers, rows) = entry
            if time.time() - ts <= ttl:
                logger.info(
                    f"cache_hit=true table_name={table_name} spreadsheet_id={spreadsheet_id[:8]}..."
                )
                return headers, rows
            # Cache expirado, borrar
            _cache.pop(key, None)

    # Cache miss: refresh con lock por tabla
    table_lock = _get_table_lock(spreadsheet_id, table_name)
    with table_lock:
        # Double-check: otro thread pudo haber refrescado
        with _cache_lock:
            entry = _cache.get(key)
            if entry:
                ts, (headers, rows) = entry
                if time.time() - ts <= ttl:
                    logger.info(
                        f"cache_hit=true table_name={table_name} spreadsheet_id={spreadsheet_id[:8]}..."
                    )
                    return headers, rows

        t0 = time.perf_counter()
        headers, rows = fetch_fn()
        t_refresh = time.perf_counter() - t0

        with _cache_lock:
            _cache[key] = (time.time(), (headers, rows))

        logger.info(
            f"cache_hit=false table_name={table_name} t_refresh={t_refresh:.3f}s "
            f"spreadsheet_id={spreadsheet_id[:8]}..."
        )
        return headers, rows


def invalidate(spreadsheet_id: str, table_name: Optional[str] = None) -> None:
    """Invalida cache. table_name=None invalida todo para ese spreadsheet."""
    with _cache_lock:
        if table_name:
            _cache.pop((spreadsheet_id, table_name), None)
        else:
            to_del = [k for k in _cache if k[0] == spreadsheet_id]
            for k in to_del:
                del _cache[k]


def invalidate_all() -> None:
    """Invalida todo el cache."""
    with _cache_lock:
        _cache.clear()
