"""
Integration tests for /api/v1/comercios endpoints.

GET, POST, PATCH, DELETE.
The comercios endpoints are built on top of regla_repo and movimiento_repo,
both of which are patched here.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import make_regla_dict

pytestmark = pytest.mark.anyio

BASE = "/api/v1/comercios"
COM_MOD = "app.api.v1.comercios"


def _make_comercio_resp(name: str = "Carrefour") -> dict:
    return {
        "id": f"comercio-carrefour",
        "name": name,
    }


# ---------------------------------------------------------------------------
# GET /comercios
# ---------------------------------------------------------------------------

class TestListComercios:
    async def test_should_return_merged_list_from_reglas_and_movimientos(self, client, auth_headers):
        reglas = [make_regla_dict()]  # comercio = "Carrefour"
        movs = ["Farmacity"]
        with (
            patch(f"{COM_MOD}.list_reglas", new_callable=AsyncMock, return_value=reglas),
            patch(f"{COM_MOD}.list_comercios_from_movimientos", new_callable=AsyncMock, return_value=movs),
        ):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "Carrefour" in names
        assert "Farmacity" in names

    async def test_should_deduplicate_comercios(self, client, auth_headers):
        reglas = [make_regla_dict()]  # Carrefour
        movs = ["Carrefour"]  # duplicate
        with (
            patch(f"{COM_MOD}.list_reglas", new_callable=AsyncMock, return_value=reglas),
            patch(f"{COM_MOD}.list_comercios_from_movimientos", new_callable=AsyncMock, return_value=movs),
        ):
            resp = await client.get(BASE, headers=auth_headers)
        assert len(resp.json()) == 1

    async def test_should_return_empty_list_when_no_data(self, client, auth_headers):
        with (
            patch(f"{COM_MOD}.list_reglas", new_callable=AsyncMock, return_value=[]),
            patch(f"{COM_MOD}.list_comercios_from_movimientos", new_callable=AsyncMock, return_value=[]),
        ):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.json() == []

    async def test_should_require_auth(self, client):
        resp = await client.get(BASE)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /comercios
# ---------------------------------------------------------------------------

class TestCreateComercio:
    async def test_should_create_comercio_with_subcategory(self, client, auth_headers):
        regla = make_regla_dict()
        regla["comercio"] = "Farmacity"
        with patch(f"{COM_MOD}.create_regla", new_callable=AsyncMock, return_value=regla):
            resp = await client.post(
                BASE,
                json={"name": "Farmacity", "defaultSubcategoryId": "10"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert "name" in body

    async def test_should_return_400_when_subcategory_id_missing(self, client, auth_headers):
        resp = await client.post(
            BASE,
            json={"name": "Farmacity"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "requerida" in resp.json()["detail"].lower()

    async def test_should_return_400_when_repo_raises_value_error(self, client, auth_headers):
        with patch(
            f"{COM_MOD}.create_regla",
            new_callable=AsyncMock,
            side_effect=ValueError("Subcategoría no encontrada"),
        ):
            resp = await client.post(
                BASE,
                json={"name": "X", "defaultSubcategoryId": "999"},
                headers=auth_headers,
            )
        assert resp.status_code == 400

    async def test_should_require_auth(self, client):
        resp = await client.post(BASE, json={"name": "X", "defaultSubcategoryId": "1"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /comercios/{id}
# ---------------------------------------------------------------------------

class TestDeleteComercio:
    async def test_should_delete_comercio_by_virtual_id(self, client, auth_headers):
        regla = make_regla_dict()
        # delete_regla is imported inside the endpoint function body, so we
        # patch it on the source module — that is where Python resolves the
        # name at import time inside the function.
        with (
            patch(f"{COM_MOD}.list_reglas", new_callable=AsyncMock, return_value=[regla]),
            patch("app.repositories.regla_repo.delete_regla", new_callable=AsyncMock, return_value=True),
        ):
            resp = await client.delete(
                f"{BASE}/comercio-carrefour",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True

    async def test_should_return_200_when_no_matching_regla(self, client, auth_headers):
        """Delete succeeds even without a regla — virtual merchant disappears on refresh."""
        with patch(f"{COM_MOD}.list_reglas", new_callable=AsyncMock, return_value=[]):
            resp = await client.delete(f"{BASE}/comercio-unknown", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["reglas_deleted"] == 0

    async def test_should_require_auth(self, client):
        resp = await client.delete(f"{BASE}/comercio-x")
        assert resp.status_code == 401
