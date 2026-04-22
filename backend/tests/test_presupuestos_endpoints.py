"""
Integration tests for /api/v1/presupuestos endpoints.

GET, POST, PATCH, DELETE.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_presupuesto_dict

pytestmark = pytest.mark.anyio

BASE = "/api/v1/presupuestos"
PRES_REPO = "app.api.v1.presupuestos"


# ---------------------------------------------------------------------------
# GET /presupuestos
# ---------------------------------------------------------------------------

class TestListPresupuestos:
    async def test_should_return_list_of_presupuestos(self, client, auth_headers):
        rows = [make_presupuesto_dict()]
        with patch(f"{PRES_REPO}.list_presupuestos", new_callable=AsyncMock, return_value=rows):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_should_filter_by_mes_anio_query_param(self, client, auth_headers):
        rows = [make_presupuesto_dict()]
        with patch(f"{PRES_REPO}.list_presupuestos", new_callable=AsyncMock, return_value=rows):
            resp = await client.get(f"{BASE}?mesAño=04/26", headers=auth_headers)
        assert resp.status_code == 200

    async def test_should_return_400_for_invalid_mes_anio(self, client, auth_headers):
        resp = await client.get(f"{BASE}?mesAño=bad-format", headers=auth_headers)
        assert resp.status_code == 400

    async def test_should_filter_in_memory_by_categoria_id(self, client, auth_headers):
        rows = [make_presupuesto_dict()]  # categoria_id = "1"
        with patch(f"{PRES_REPO}.list_presupuestos", new_callable=AsyncMock, return_value=rows):
            resp = await client.get(f"{BASE}?categoria_id=99", headers=auth_headers)
        # categoria_id=99 does not match categoria_id="1"
        assert resp.json() == []

    async def test_should_require_auth(self, client):
        resp = await client.get(BASE)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /presupuestos
# ---------------------------------------------------------------------------

class TestCreatePresupuesto:
    VALID_PAYLOAD = {
        "categoryId": "1",
        "amount": 5000,
        "mes_anio": "04/26",
    }

    async def test_should_create_presupuesto(self, client, auth_headers):
        row = make_presupuesto_dict()
        row["categoria_id"] = "1"
        row["subcategoria_id"] = ""
        with patch(f"{PRES_REPO}.upsert_presupuesto", new_callable=AsyncMock, return_value=row):
            resp = await client.post(BASE, json=self.VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["categoryId"] == "1"
        assert body["amount"] == float(row["monto"])

    async def test_should_return_400_when_amount_is_zero(self, client, auth_headers):
        resp = await client.post(BASE, json={**self.VALID_PAYLOAD, "amount": 0}, headers=auth_headers)
        assert resp.status_code == 400
        assert "mayor a 0" in resp.json()["detail"]

    async def test_should_return_400_when_amount_is_negative(self, client, auth_headers):
        resp = await client.post(BASE, json={**self.VALID_PAYLOAD, "amount": -1}, headers=auth_headers)
        assert resp.status_code == 400

    async def test_should_return_400_when_categoryId_is_not_numeric(self, client, auth_headers):
        resp = await client.post(BASE, json={**self.VALID_PAYLOAD, "categoryId": "abc"}, headers=auth_headers)
        assert resp.status_code == 400
        assert "categoryId" in resp.json()["detail"]

    async def test_should_use_current_month_when_mes_anio_omitted(self, client, auth_headers):
        """When mes_anio is not supplied, the endpoint defaults to current month."""
        row = make_presupuesto_dict()
        row["categoria_id"] = "1"
        row["subcategoria_id"] = ""
        with patch(f"{PRES_REPO}.upsert_presupuesto", new_callable=AsyncMock, return_value=row):
            resp = await client.post(
                BASE,
                json={"categoryId": "1", "amount": 5000},
                headers=auth_headers,
            )
        assert resp.status_code == 200

    async def test_should_require_auth(self, client):
        resp = await client.post(BASE, json=self.VALID_PAYLOAD)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /presupuestos/{id}
# ---------------------------------------------------------------------------

class TestPatchPresupuesto:
    async def test_should_update_monto(self, client, auth_headers, mock_db):
        existing = make_presupuesto_dict()
        updated = {**existing, "monto": 9000.0}

        mock_presupuesto_obj = MagicMock()
        mock_presupuesto_obj.Monto = 5000

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = mock_presupuesto_obj
        mock_db.execute = AsyncMock(return_value=execute_result)

        with (
            patch(f"{PRES_REPO}.get_presupuesto", new_callable=AsyncMock, side_effect=[existing, updated]),
        ):
            resp = await client.patch(
                f"{BASE}/300",
                json={"amount": 9000},
                headers=auth_headers,
            )
        assert resp.status_code == 200

    async def test_should_return_404_when_not_found(self, client, auth_headers):
        with patch(f"{PRES_REPO}.get_presupuesto", new_callable=AsyncMock, return_value=None):
            resp = await client.patch(f"{BASE}/999", json={"amount": 100}, headers=auth_headers)
        assert resp.status_code == 404

    async def test_should_return_400_when_monto_not_positive(self, client, auth_headers):
        resp = await client.patch(f"{BASE}/300", json={"amount": 0}, headers=auth_headers)
        assert resp.status_code == 400

    async def test_should_return_existing_when_no_patch_fields(self, client, auth_headers):
        pres = make_presupuesto_dict()
        with patch(f"{PRES_REPO}.get_presupuesto", new_callable=AsyncMock, return_value=pres):
            resp = await client.patch(f"{BASE}/300", json={}, headers=auth_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# DELETE /presupuestos/{id}
# ---------------------------------------------------------------------------

class TestDeletePresupuesto:
    async def test_should_delete_and_return_confirmation(self, client, auth_headers):
        with patch(f"{PRES_REPO}.delete_presupuesto", new_callable=AsyncMock, return_value=True):
            resp = await client.delete(f"{BASE}/300", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    async def test_should_return_404_when_not_found(self, client, auth_headers):
        with patch(f"{PRES_REPO}.delete_presupuesto", new_callable=AsyncMock, return_value=False):
            resp = await client.delete(f"{BASE}/999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_should_require_auth(self, client):
        resp = await client.delete(f"{BASE}/1")
        assert resp.status_code == 401
