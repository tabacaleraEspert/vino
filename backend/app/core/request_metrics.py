"""
Métricas por request para identificar cuellos de botella.
request_id, path, t_total, t_sql, t_sheets
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Generator

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_request_start_var: ContextVar[float | None] = ContextVar("request_start", default=None)

# Dict compartido: request_id -> {t_sql, t_sheets}. Thread-safe.
_metrics: Dict[str, dict] = {}
_metrics_lock = threading.Lock()

logger = logging.getLogger(__name__)


def set_request_context(request_id: str) -> None:
    """Setea request_id y start time (llamado por middleware)."""
    _request_id_var.set(request_id)
    _request_start_var.set(time.perf_counter())


def get_request_id() -> str | None:
    return _request_id_var.get()


def add_sql_time(seconds: float) -> None:
    """Acumula tiempo de SQL en el request actual."""
    rid = _request_id_var.get()
    if rid:
        with _metrics_lock:
            if rid not in _metrics:
                _metrics[rid] = {"t_sql": 0.0, "t_sheets": 0.0}
            _metrics[rid]["t_sql"] += seconds


def add_sheets_time(seconds: float) -> None:
    """Acumula tiempo de Sheets en el request actual."""
    rid = _request_id_var.get()
    if rid:
        with _metrics_lock:
            if rid not in _metrics:
                _metrics[rid] = {"t_sql": 0.0, "t_sheets": 0.0}
            _metrics[rid]["t_sheets"] += seconds


def get_and_clear_metrics(request_id: str) -> dict:
    """Obtiene métricas y las elimina (llamado por middleware al final)."""
    with _metrics_lock:
        m = _metrics.pop(request_id, {"t_sql": 0.0, "t_sheets": 0.0})
    return m


@contextmanager
def time_sql_block() -> Generator[None, None, None]:
    """Context manager para medir tiempo de bloque SQL."""
    start = time.perf_counter()
    try:
        yield
    finally:
        add_sql_time(time.perf_counter() - start)


@contextmanager
def time_sheets_block() -> Generator[None, None, None]:
    """Context manager para medir tiempo de bloque Sheets."""
    start = time.perf_counter()
    try:
        yield
    finally:
        add_sheets_time(time.perf_counter() - start)
