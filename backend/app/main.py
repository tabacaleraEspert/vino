import logging
import threading
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.metrics import RequestMetricsMiddleware

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Finanzas Personales API",
    version=settings.APP_VERSION,
)

# Métricas por request: request_id, path, t_total, t_sql, t_sheets (para identificar cuellos)
app.add_middleware(RequestMetricsMiddleware)

# CORS: Azure Portal puede tener su propia CORS que anula esta. Si falla, en Portal → CORS
# vacía todos los orígenes para que la app maneje CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "https://lively-sand-05dbb8b0f.1.azurestaticapps.net",
        *settings.CORS_ORIGINS,
    ],
    allow_origin_regex=r"https://[a-zA-Z0-9.-]+\.azurestaticapps\.net|http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


def _prefetch_tables() -> None:
    """Precarga tablas críticas cuando SPREADSHEET_ID está configurado (dev/backfill)."""
    sid = settings.SPREADSHEET_ID
    if not sid:
        return
    from app.sheets.registry import set_current_spreadsheet_id
    from app.sheets.service import read_table

    set_current_spreadsheet_id(sid)
    tables = ["reglas", "categorias", "subcategorias"]  # presupuestos ahora en SQL
    for t in tables:
        try:
            read_table(t)
            logger.info(f"prefetch ok: {t}")
        except Exception as e:
            logger.warning(f"prefetch {t}: {e}")


def _refresh_loop() -> None:
    """Refresco periódico de cache cada SHEETS_REFRESH_INTERVAL_SEC."""
    interval = settings.SHEETS_REFRESH_INTERVAL_SEC
    if interval <= 0:
        return
    sid = settings.SPREADSHEET_ID
    if not sid:
        return
    from app.sheets.registry import set_current_spreadsheet_id
    from app.sheets.service import read_table

    set_current_spreadsheet_id(sid)
    tables = ["reglas", "categorias", "subcategorias"]  # presupuestos ahora en SQL
    while True:
        time.sleep(interval)
        for t in tables:
            try:
                read_table(t)
                logger.info(f"refresh ok: {t}")
            except Exception as e:
                logger.warning(f"refresh {t}: {e}")


@app.on_event("startup")
def startup_event() -> None:
    # Prefetch en background (solo si SPREADSHEET_ID está set)
    t = threading.Thread(target=_prefetch_tables, daemon=True)
    t.start()
    # Refresco periódico en background
    if settings.SHEETS_REFRESH_INTERVAL_SEC > 0 and settings.SPREADSHEET_ID:
        tr = threading.Thread(target=_refresh_loop, daemon=True)
        tr.start()
