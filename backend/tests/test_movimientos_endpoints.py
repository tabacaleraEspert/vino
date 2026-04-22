"""
Integration tests for /api/v1/movimientos endpoints.

All repository functions are patched so no DB connection is needed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import auth_headers, make_movimiento_dict

pytestmark = pytest.mark.anyio

BASE = "/api/v1/movimientos"

MOV_REPO = "app.api.v1.movimientos"


# ---------------------------------------------------------------------------
# GET /movimientos  (list)
# ---------------------------------------------------------------------------

class TestListMovimientos:
    async def test_should_return_paginated_list(self, client, auth_headers):
        mov = make_movimiento_dict()
        with patch(f"{MOV_REPO}.repo_list", new_callable=AsyncMock, return_value=([mov], 1)):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == mov["id"]

    async def test_should_return_empty_list_when_no_movimientos(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_list", new_callable=AsyncMock, return_value=([], 0)):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    async def test_should_require_auth(self, client):
        resp = await client.get(BASE)
        assert resp.status_code == 401

    async def test_should_accept_period_query_param(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_list", new_callable=AsyncMock, return_value=([], 0)):
            resp = await client.get(f"{BASE}?period=2026-04", headers=auth_headers)
        assert resp.status_code == 200

    async def test_should_default_tipo_to_gasto(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_list", new_callable=AsyncMock, return_value=([], 0)) as mock_list:
            await client.get(BASE, headers=auth_headers)
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs.get("tipo") == "Gasto"

    async def test_should_normalize_ingreso_tipo(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_list", new_callable=AsyncMock, return_value=([], 0)) as mock_list:
            await client.get(f"{BASE}?tipo=INGRESO", headers=auth_headers)
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs.get("tipo") == "Ingreso"

    async def test_should_respect_pagination_params(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_list", new_callable=AsyncMock, return_value=([], 0)):
            resp = await client.get(f"{BASE}?page=2&limit=10", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 2
        assert body["limit"] == 10

    async def test_should_reject_limit_over_100(self, client, auth_headers):
        resp = await client.get(f"{BASE}?limit=101", headers=auth_headers)
        assert resp.status_code == 422

    async def test_should_reject_page_zero(self, client, auth_headers):
        resp = await client.get(f"{BASE}?page=0", headers=auth_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /movimientos/{id}
# ---------------------------------------------------------------------------

class TestGetMovimiento:
    async def test_should_return_movimiento_by_id(self, client, auth_headers):
        mov = make_movimiento_dict(mov_id=100)
        with patch(f"{MOV_REPO}.repo_get", new_callable=AsyncMock, return_value=mov):
            resp = await client.get(f"{BASE}/100", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["Id"] == 100

    async def test_should_return_404_when_not_found(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_get", new_callable=AsyncMock, return_value=None):
            resp = await client.get(f"{BASE}/999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_should_require_auth(self, client):
        resp = await client.get(f"{BASE}/1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /movimientos
# ---------------------------------------------------------------------------

class TestCreateMovimiento:
    VALID_PAYLOAD = {
        "Fecha": "2026-04-01",
        "Monto": 1500,
        "TipoMovimiento": "Gasto",
        "Moneda": "ARS",
    }

    async def test_should_create_and_return_movimiento(self, client, auth_headers):
        mov = make_movimiento_dict()
        with patch(f"{MOV_REPO}.repo_create", new_callable=AsyncMock, return_value=mov):
            resp = await client.post(BASE, json=self.VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["Id"] == mov["Id"]

    async def test_should_return_400_when_fecha_is_missing(self, client, auth_headers):
        payload = {k: v for k, v in self.VALID_PAYLOAD.items() if k != "Fecha"}
        resp = await client.post(BASE, json=payload, headers=auth_headers)
        assert resp.status_code == 400
        assert "Fecha" in resp.json()["detail"]

    async def test_should_return_400_when_monto_is_negative(self, client, auth_headers):
        payload = {**self.VALID_PAYLOAD, "Monto": -100}
        resp = await client.post(BASE, json=payload, headers=auth_headers)
        assert resp.status_code == 400
        assert "Monto" in resp.json()["detail"]

    async def test_should_accept_monto_zero(self, client, auth_headers):
        mov = make_movimiento_dict()
        with patch(f"{MOV_REPO}.repo_create", new_callable=AsyncMock, return_value=mov):
            resp = await client.post(BASE, json={**self.VALID_PAYLOAD, "Monto": 0}, headers=auth_headers)
        assert resp.status_code == 200

    async def test_should_normalize_ingreso_tipo(self, client, auth_headers):
        mov = make_movimiento_dict()
        with patch(f"{MOV_REPO}.repo_create", new_callable=AsyncMock, return_value=mov) as mock_create:
            await client.post(BASE, json={**self.VALID_PAYLOAD, "TipoMovimiento": "ingreso"}, headers=auth_headers)
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["tipo"] == "Ingreso"

    async def test_should_default_medio_carga_to_manual(self, client, auth_headers):
        mov = make_movimiento_dict()
        with patch(f"{MOV_REPO}.repo_create", new_callable=AsyncMock, return_value=mov) as mock_create:
            await client.post(BASE, json=self.VALID_PAYLOAD, headers=auth_headers)
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["medio_carga"] == "Manual"

    async def test_should_require_auth(self, client):
        resp = await client.post(BASE, json=self.VALID_PAYLOAD)
        assert resp.status_code == 401

    async def test_should_accept_snake_case_field_names(self, client, auth_headers):
        mov = make_movimiento_dict()
        payload = {"fecha": "2026-04-01", "monto": 500, "tipo": "Gasto"}
        with patch(f"{MOV_REPO}.repo_create", new_callable=AsyncMock, return_value=mov):
            resp = await client.post(BASE, json=payload, headers=auth_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /movimientos/{id}
# ---------------------------------------------------------------------------

class TestPatchMovimiento:
    async def test_should_update_and_return_movimiento(self, client, auth_headers):
        updated = make_movimiento_dict()
        updated["monto"] = 2000.0
        with patch(f"{MOV_REPO}.repo_update", new_callable=AsyncMock, return_value=updated):
            resp = await client.patch(
                f"{BASE}/100",
                json={"Monto": 2000},
                headers=auth_headers,
            )
        assert resp.status_code == 200

    async def test_should_return_404_when_movimiento_not_found(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_update", new_callable=AsyncMock, return_value=None):
            resp = await client.patch(
                f"{BASE}/999",
                json={"Monto": 2000},
                headers=auth_headers,
            )
        assert resp.status_code == 404

    async def test_should_return_existing_when_no_fields_to_update(self, client, auth_headers):
        existing = make_movimiento_dict()
        with patch(f"{MOV_REPO}.repo_get", new_callable=AsyncMock, return_value=existing):
            resp = await client.patch(f"{BASE}/100", json={}, headers=auth_headers)
        assert resp.status_code == 200

    async def test_should_return_404_when_empty_patch_and_not_found(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_get", new_callable=AsyncMock, return_value=None):
            resp = await client.patch(f"{BASE}/999", json={}, headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /movimientos/{id}
# ---------------------------------------------------------------------------

class TestDeleteMovimiento:
    async def test_should_delete_and_return_confirmation(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_delete", new_callable=AsyncMock, return_value=True):
            resp = await client.delete(f"{BASE}/100", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True
        assert body["id"] == "100"

    async def test_should_return_404_when_not_found(self, client, auth_headers):
        with patch(f"{MOV_REPO}.repo_delete", new_callable=AsyncMock, return_value=False):
            resp = await client.delete(f"{BASE}/999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_should_require_auth(self, client):
        resp = await client.delete(f"{BASE}/1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /movimientos/invalidate-cache
# ---------------------------------------------------------------------------

class TestInvalidateCache:
    async def test_should_return_ok_no_op(self, client, auth_headers):
        resp = await client.post(f"{BASE}/invalidate-cache", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
