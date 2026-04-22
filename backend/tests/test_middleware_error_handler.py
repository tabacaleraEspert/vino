"""
Tests for the global error handlers registered in app.middleware.error_handler.

Strategy:
- IntegrityError, OperationalError, ValueError: inject via a temporary route
  added to the FULL main app (which has all middleware including the error
  handlers registered on startup).  We add/remove the route around each test.
- Generic Exception handler: tested by examining the handler function directly
  (the Starlette ServerErrorMiddleware re-raises bare exceptions before our
  handler in test mode, so we call the handler directly instead).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from sqlalchemy.exc import IntegrityError, OperationalError

from app.middleware.error_handler import register_error_handlers

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Shared mini-app for error handler tests (re-uses the main app via client)
# ---------------------------------------------------------------------------

class TestIntegrityError:
    async def test_integrity_error_returns_409(self, client, auth_headers):
        from app.main import app
        from fastapi.routing import APIRoute

        async def _raise(request: Request):
            raise IntegrityError("dup", {}, Exception("orig"))

        route = APIRoute("/test-integrity-error", _raise, methods=["GET"])
        app.routes.append(route)
        try:
            resp = await client.get("/test-integrity-error", headers=auth_headers)
        finally:
            app.routes.remove(route)

        assert resp.status_code == 409
        assert "Conflicto" in resp.json()["detail"]


class TestOperationalError:
    async def test_operational_error_returns_503(self, client, auth_headers):
        from app.main import app
        from fastapi.routing import APIRoute

        async def _raise(request: Request):
            raise OperationalError("conn", {}, Exception("orig"))

        route = APIRoute("/test-operational-error", _raise, methods=["GET"])
        app.routes.append(route)
        try:
            resp = await client.get("/test-operational-error", headers=auth_headers)
        finally:
            app.routes.remove(route)

        assert resp.status_code == 503
        assert "no disponible" in resp.json()["detail"]


class TestValueError:
    async def test_value_error_returns_400(self, client, auth_headers):
        from app.main import app
        from fastapi.routing import APIRoute

        async def _raise(request: Request):
            raise ValueError("campo inválido")

        route = APIRoute("/test-value-error", _raise, methods=["GET"])
        app.routes.append(route)
        try:
            resp = await client.get("/test-value-error", headers=auth_headers)
        finally:
            app.routes.remove(route)

        assert resp.status_code == 400
        assert resp.json()["detail"] == "campo inválido"


class TestGenericExceptionHandler:
    """Test the generic Exception handler function directly.

    We extract the handler by inspecting the app's exception_handlers dict
    after register_error_handlers runs.
    """

    async def test_generic_handler_returns_500_json(self):
        import json
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        mini = FastAPI()
        register_error_handlers(mini)

        # FastAPI stores handlers in exception_handlers dict keyed by type
        generic_handler = mini.exception_handlers.get(Exception)
        assert generic_handler is not None, "Generic Exception handler not registered"

        mock_request = MagicMock()
        mock_request.url.path = "/test"

        response = await generic_handler(mock_request, RuntimeError("boom"))

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        body = json.loads(response.body)
        assert "boom" not in body["detail"]
        assert "interno" in body["detail"].lower()
