"""
Shared fixtures for all backend tests.

Strategy:
- Override get_db FastAPI dependency with a mock AsyncSession so tests never
  touch the real Azure SQL Server.
- Build a valid JWT token from the same secret the app uses (dev default).
- Provide factory helpers that return realistic domain dicts matching what
  repositories return (so endpoint logic sees the same shape as production).

Note on pyodbc / aioodbc:
  These are native C extensions that require the ODBC SDK at build time.
  In environments where they cannot be installed (CI without ODBC headers),
  we stub them in sys.modules before any app import so the test suite can
  still be collected and run.  The stubs have no real behaviour — actual DB
  calls are fully mocked via the get_db dependency override.
"""
from __future__ import annotations

import sys
import types
from datetime import date, datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Stub native C extensions that may be absent in test environments
# ---------------------------------------------------------------------------

def _stub_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


for _ext in ("pyodbc", "aioodbc"):
    if _ext not in sys.modules:
        _stub_module(_ext)
        # aioodbc exposes create_async_engine-compatible objects; stub enough
        # to survive import but never actually connect.
        sys.modules[_ext].connect = MagicMock()
        sys.modules[_ext].Connection = MagicMock()

from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# pytest-asyncio configuration
# ---------------------------------------------------------------------------
pytest_plugins = ("anyio",)


# ---------------------------------------------------------------------------
# Mock DB session
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_db() -> AsyncMock:
    """A fully mocked AsyncSession. Individual tests configure return values."""
    session = AsyncMock()
    # execute() returns an object with helper methods
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    execute_result.scalar_one.return_value = 0
    execute_result.scalars.return_value.all.return_value = []
    execute_result.first.return_value = None
    execute_result.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# HTTP client with dependency override
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client(mock_db: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with the real app but the DB dependency mocked out."""

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

USER_ID = 42
USERNAME = "testuser"


def make_token(user_id: int = USER_ID) -> str:
    """Create a valid JWT for test user."""
    return create_access_token(sub=str(user_id))


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token()}"}


# ---------------------------------------------------------------------------
# Sample domain data factories
# These mirror the dict shape returned by the real repositories.
# ---------------------------------------------------------------------------

def make_user_dict(
    user_id: int = USER_ID,
    nombre: str = USERNAME,
    apellido: str = "Apellido",
    password: str = "secret123",
) -> dict:
    return {
        "id": user_id,
        "Id": user_id,
        "Nombre": nombre,
        "Apellido": apellido,
        "gmail": "test@example.com",
        "PasswordHash": hash_password(password),
        "ID_Sheets": "",
    }


def make_categoria_dict(cat_id: int = 1, nombre: str = "Alimentacion") -> dict:
    return {
        "id": cat_id,
        "nombre": nombre,
        "icon": "🍔",
        "color": "#ff5733",
    }


def make_subcategoria_dict(
    sub_id: int = 10,
    categoria_id: int = 1,
    nombre: str = "Supermercado",
) -> dict:
    return {
        "id": sub_id,
        "categoria_id": categoria_id,
        "nombre": nombre,
    }


def make_movimiento_dict(mov_id: int = 100) -> dict:
    return {
        "id": str(mov_id),
        "Id": mov_id,
        "fecha": "2026-04-01",
        "Fecha": "2026-04-01",
        "timestamp": "2026-04-01T10:00:00",
        "Timestamp": "2026-04-01T10:00:00",
        "tipo": "Gasto",
        "moneda": "ARS",
        "Moneda": "ARS",
        "monto": 1500.0,
        "Monto": 1500.0,
        "comercio": "Carrefour",
        "Comercio": "Carrefour",
        "comercioId": None,
        "descripcion": "Carrefour",
        "Descripcion": "Carrefour",
        "categoria": "Alimentacion",
        "Nombre_Categoria": "Alimentacion",
        "subcategoria": "Supermercado",
        "Nombre_SubCategoria": "Supermercado",
        "idCategoria": "1",
        "idSubcategoria": "10",
        "Id_Categoria": 1,
        "Id_SubCategoria": 10,
        "MedioCarga": "Manual",
        "medio_carga": "Manual",
        "Id_Credito_Debito": None,
        "Id_Medio_Pago_Final": None,
        "Origen": None,
        "Origen_Id": None,
    }


def make_regla_dict(regla_id: int = 200) -> dict:
    return {
        "id": regla_id,
        "comercio": "Carrefour",
        "patron": "Carrefour",
        "patron_norm": "carrefour",
        "categoria_id": 1,
        "categoria_nombre": "Alimentacion",
        "subcategoria_id": 10,
        "subcategoria_nombre": "Supermercado",
        "prioridad": 100,
        "activa": True,
        "confianza": "MANUAL",
        "timestamp": "2026-04-01T10:00:00",
    }


def make_presupuesto_dict(pres_id: int = 300) -> dict:
    return {
        "id": pres_id,
        "mes_anio": "04/26",
        "categoria_id": "1",
        "categoria_nombre": "Alimentacion",
        "subcategoria_id": "10",
        "subcategoria_nombre": "Supermercado",
        "monto": 5000.0,
    }
