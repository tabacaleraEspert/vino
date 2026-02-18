"""
Middleware de métricas por request.
Log: request_id, path, t_total, t_sql, t_sheets
"""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_metrics import (
    get_and_clear_metrics,
    set_request_context,
)
import logging

logger = logging.getLogger(__name__)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        set_request_context(request_id)
        start = time.perf_counter()

        response = await call_next(request)

        t_total = time.perf_counter() - start
        m = get_and_clear_metrics(request_id)
        path = request.scope.get("path", "/")
        logger.info(
            f"request_id={request_id} path={path} "
            f"t_total={t_total:.3f}s t_sql={m['t_sql']:.3f}s t_sheets={m['t_sheets']:.3f}s"
        )
        return response
