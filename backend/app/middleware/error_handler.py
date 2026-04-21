"""Global exception handlers - never leak internal details to the client."""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("IntegrityError: %s path=%s", exc.orig, request.url.path)
        return JSONResponse(
            status_code=409,
            content={"detail": "Conflicto: el recurso ya existe o viola una restricción"},
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError):
        logger.error("OperationalError: %s path=%s", exc.orig, request.url.path)
        return JSONResponse(
            status_code=503,
            content={"detail": "Servicio temporalmente no disponible"},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s path=%s", type(exc).__name__, request.url.path, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor"},
        )
