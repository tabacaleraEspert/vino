"""
Integration tests for GET /api/v1/bootstrap.

The bootstrap endpoint aggregates data from 5 repositories in a single call.
All repos are patched so no DB connection is made.
"""
from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import (
    make_categoria_dict,
    make_presupuesto_dict,
    make_regla_dict,
    make_subcategoria_dict,
)

pytestmark = pytest.mark.anyio

BASE = "/api/v1/bootstrap"
BOOT_MOD = "app.api.v1.bootstrap"


def _patch_all_repos(
    categorias=None,
    subcategorias=None,
    reglas=None,
    presupuestos=None,
    comercios_movs=None,
):
    """Return an ExitStack that patches all 5 bootstrap repositories."""
    stack = ExitStack()
    stack.enter_context(patch(f"{BOOT_MOD}.list_categorias", new_callable=AsyncMock, return_value=categorias or []))
    stack.enter_context(patch(f"{BOOT_MOD}.list_subcategorias", new_callable=AsyncMock, return_value=subcategorias or []))
    stack.enter_context(patch(f"{BOOT_MOD}.list_reglas", new_callable=AsyncMock, return_value=reglas or []))
    stack.enter_context(patch(f"{BOOT_MOD}.list_presupuestos", new_callable=AsyncMock, return_value=presupuestos or []))
    stack.enter_context(patch(f"{BOOT_MOD}.list_comercios_from_movimientos", new_callable=AsyncMock, return_value=comercios_movs or []))
    return stack


class TestBootstrap:
    async def test_should_return_all_catalog_keys(self, client, auth_headers):
        with _patch_all_repos(
            categorias=[make_categoria_dict()],
            subcategorias=[make_subcategoria_dict()],
            reglas=[make_regla_dict()],
            presupuestos=[make_presupuesto_dict()],
            comercios_movs=["Farmacity"],
        ):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "categorias" in body
        assert "subcategorias" in body
        assert "reglas" in body
        assert "presupuestos" in body
        assert "comercios" in body

    async def test_should_return_correct_counts(self, client, auth_headers):
        with _patch_all_repos(
            categorias=[make_categoria_dict(1), make_categoria_dict(2)],
            subcategorias=[make_subcategoria_dict()],
            reglas=[make_regla_dict()],
            presupuestos=[make_presupuesto_dict()],
            comercios_movs=["Farmacity"],
        ):
            resp = await client.get(BASE, headers=auth_headers)
        body = resp.json()
        assert len(body["categorias"]) == 2
        assert len(body["subcategorias"]) == 1
        assert len(body["reglas"]) == 1
        assert len(body["presupuestos"]) == 1

    async def test_should_include_regla_fields_in_response(self, client, auth_headers):
        regla = make_regla_dict()
        with _patch_all_repos(reglas=[regla]):
            resp = await client.get(BASE, headers=auth_headers)
        r = resp.json()["reglas"][0]
        assert r["id"] == regla["id"]
        assert r["comercio"] == regla["comercio"]
        assert r["categoria_id"] == regla["categoria_id"]
        assert r["subcategoria_id"] == regla["subcategoria_id"]

    async def test_should_include_presupuesto_fields_in_response(self, client, auth_headers):
        pres = make_presupuesto_dict()
        with _patch_all_repos(presupuestos=[pres]):
            resp = await client.get(BASE, headers=auth_headers)
        p = resp.json()["presupuestos"][0]
        assert p["id"] == pres["id"]
        assert p["mes_anio"] == pres["mes_anio"]
        assert p["monto"] == pres["monto"]

    async def test_should_merge_comercios_from_reglas_and_movimientos(self, client, auth_headers):
        regla = make_regla_dict()  # comercio = "Carrefour"
        with _patch_all_repos(reglas=[regla], comercios_movs=["Farmacity"]):
            resp = await client.get(BASE, headers=auth_headers)
        names = [c["name"] for c in resp.json()["comercios"]]
        assert "Carrefour" in names
        assert "Farmacity" in names

    async def test_should_deduplicate_comercios(self, client, auth_headers):
        regla = make_regla_dict()  # Carrefour
        with _patch_all_repos(reglas=[regla], comercios_movs=["Carrefour"]):
            resp = await client.get(BASE, headers=auth_headers)
        names = [c["name"] for c in resp.json()["comercios"]]
        assert names.count("Carrefour") == 1

    async def test_should_return_empty_catalogs_when_no_data(self, client, auth_headers):
        with _patch_all_repos():
            resp = await client.get(BASE, headers=auth_headers)
        body = resp.json()
        assert body["categorias"] == []
        assert body["subcategorias"] == []
        assert body["reglas"] == []
        assert body["presupuestos"] == []
        assert body["comercios"] == []

    async def test_should_require_auth(self, client):
        resp = await client.get(BASE)
        assert resp.status_code == 401
