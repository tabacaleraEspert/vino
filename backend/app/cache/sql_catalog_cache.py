"""
Cache in-memory para catálogos SQL (categorías, subcategorías, reglas, presupuestos).
Reduce round-trips a Azure SQL cuando los datos cambian poco.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_CACHE: Dict[tuple, tuple] = {}  # (id_usuario, key) -> (data, timestamp)
_LOCK = threading.Lock()


def get_cached(
    id_usuario: int,
    key: str,
    fetch_fn: Callable[[], Any],
    ttl_sec: int,
) -> Any:
    """
    Obtiene datos de cache o ejecuta fetch_fn.
    key: "categorias" | "subcategorias" | "reglas" | "presupuestos"
    """
    if ttl_sec <= 0:
        return fetch_fn()

    cache_key = (id_usuario, key)
    with _LOCK:
        entry = _CACHE.get(cache_key)
        if entry:
            data, ts = entry
            if time.time() - ts <= ttl_sec:
                logger.debug("sql_catalog_cache_hit key=%s id_usuario=%s", key, id_usuario)
                return data
            _CACHE.pop(cache_key, None)

    data = fetch_fn()
    with _LOCK:
        _CACHE[cache_key] = (data, time.time())
    return data


def invalidate(id_usuario: int, key: Optional[str] = None) -> None:
    """Invalida cache. key=None invalida todo para ese usuario."""
    with _LOCK:
        if key:
            _CACHE.pop((id_usuario, key), None)
        else:
            to_del = [k for k in _CACHE if k[0] == id_usuario]
            for k in to_del:
                del _CACHE[k]
