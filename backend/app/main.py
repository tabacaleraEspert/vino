import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.metrics import RequestMetricsMiddleware

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Finanzas API v%s (env=%s)", settings.APP_VERSION, settings.ENV)
    yield
    # Cleanup: dispose async engine
    from app.db.session import _async_engine
    if _async_engine:
        await _async_engine.dispose()
    logger.info("Finanzas API shutdown complete")


app = FastAPI(
    title="Finanzas Personales API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Compresión gzip para responses >500 bytes (mobile-first: ahorra bandwidth)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(RequestMetricsMiddleware)

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

# Global error handlers - never leak internal details
from app.middleware.error_handler import register_error_handlers
register_error_handlers(app)
