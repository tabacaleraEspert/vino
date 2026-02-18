"""
Cache in-memory para read_table. TTL en segundos.
Reduce llamadas a Google Sheets API.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

# (spreadsheet_id, entity) -> (headers, rows, timestamp)
_cache: Dict[tuple, tuple] = {}
_cache_lock = threading.Lock()


def _get_cached(
    spreadsheet_id: str, entity: str
) -> Optional[Tuple[List[str], List[Dict[str, Any]]]]:
    ttl = settings.SHEETS_CACHE_TTL_SEC
    if ttl <= 0:
        return None

    key = (spreadsheet_id, entity)
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        headers, rows, ts = entry
        if time.time() - ts > ttl:
            del _cache[key]
            return None
        return headers, rows


def _set_cached(
    spreadsheet_id: str,
    entity: str,
    headers: List[str],
    rows: List[Dict[str, Any]],
) -> None:
    ttl = settings.SHEETS_CACHE_TTL_SEC
    if ttl <= 0:
        return

    key = (spreadsheet_id, entity)
    with _cache_lock:
        _cache[key] = (headers, rows, time.time())


def invalidate(spreadsheet_id: str, entity: Optional[str] = None) -> None:
    """Invalida cache. entity=None invalida todo para ese spreadsheet."""
    with _cache_lock:
        if entity:
            _cache.pop((spreadsheet_id, entity), None)
        else:
            to_del = [k for k in _cache if k[0] == spreadsheet_id]
            for k in to_del:
                del _cache[k]
