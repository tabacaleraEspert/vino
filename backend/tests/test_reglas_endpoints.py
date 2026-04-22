"""
Integration tests for /api/v1/reglas endpoints.

GET, POST (nuevo format + legacy merchantId), POST /resolve, PATCH, DELETE.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import make_regla_dict

pytestmark = pytest.mark.anyio

BASE = "/api/v1/reglas"
REGLA_REPO = "app.api.v1.reglas"


# ---------------------------------------------------------------------------
# GET /reglas
# ---------------------------------------------------------------------------

class TestListReglas:
    async def test_should_return_list_of_reglas(self, client, auth_headers):
        reglas = [make_regla_dict(1), make_regla_dict(2)]
        with patch(f"{REGLA_REPO}.list_reglas", new_callable=AsyncMock, return_value=reglas):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_should_filter_by_comercio(self, client, auth_headers):
        reglas = [make_regla_dict()]
        with patch(f"{REGLA_REPO}.list_reglas", new_callable=AsyncMock, return_value=reglas):
            resp = await client.get(f"{BASE}?comercio=Carrefour", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_should_filter_out_unmatched_comercio(self, client, auth_headers):
        reglas = [make_regla_dict()]  # comercio = "Carrefour"
        with patch(f"{REGLA_REPO}.list_reglas", new_callable=AsyncMock, return_value=reglas):
            resp = await client.get(f"{BASE}?comercio=Farmacity", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_should_filter_by_categoria_id(self, client, auth_headers):
        reglas = [make_regla_dict()]  # categoria_id = 1
        with patch(f"{REGLA_REPO}.list_reglas", new_callable=AsyncMock, return_value=reglas):
            resp = await client.get(f"{BASE}?categoria_id=1", headers=auth_headers)
        assert len(resp.json()) == 1

    async def test_should_require_auth(self, client):
        resp = await client.get(BASE)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /reglas  (nuevo formato)
# ---------------------------------------------------------------------------

class TestCreateRegla:
    async def test_should_create_regla_with_new_format(self, client, auth_headers):
        regla = make_regla_dict()
        with patch(f"{REGLA_REPO}.create_regla", new_callable=AsyncMock, return_value=regla):
            resp = await client.post(
                BASE,
                json={"patron": "Carrefour", "idSubcategoria": "10"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == regla["id"]
        assert body["comercio"] == regla["comercio"]

    async def test_should_return_400_when_patron_is_empty(self, client, auth_headers):
        resp = await client.post(
            BASE,
            json={"patron": "", "idSubcategoria": "10"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "patron" in resp.json()["detail"]

    async def test_should_return_400_when_idSubcategoria_is_missing(self, client, auth_headers):
        resp = await client.post(
            BASE,
            json={"patron": "Carrefour"},
            headers=auth_headers,
        )
        # Neither new nor legacy format matched -> 400
        assert resp.status_code == 400

    async def test_should_return_400_when_repo_raises_value_error(self, client, auth_headers):
        with patch(
            f"{REGLA_REPO}.create_regla",
            new_callable=AsyncMock,
            side_effect=ValueError("Subcategoría no encontrada"),
        ):
            resp = await client.post(
                BASE,
                json={"patron": "X", "idSubcategoria": "999"},
                headers=auth_headers,
            )
        assert resp.status_code == 400

    async def test_should_create_regla_with_legacy_merchant_format(self, client, auth_headers):
        regla = make_regla_dict()
        with patch(f"{REGLA_REPO}.create_regla", new_callable=AsyncMock, return_value=regla):
            resp = await client.post(
                BASE,
                json={"merchantId": "comercio-Carrefour", "subcategoryId": "10"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert "merchantId" in resp.json()

    async def test_should_return_400_for_invalid_body(self, client, auth_headers):
        resp = await client.post(BASE, json={"random": "field"}, headers=auth_headers)
        assert resp.status_code == 400

    async def test_should_require_auth(self, client):
        resp = await client.post(BASE, json={"patron": "X", "idSubcategoria": "1"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /reglas/resolve
# ---------------------------------------------------------------------------

class TestResolveRegla:
    async def test_should_return_match_when_regla_found(self, client, auth_headers):
        regla = make_regla_dict()
        with patch(f"{REGLA_REPO}.resolve_regla", new_callable=AsyncMock, return_value=regla):
            resp = await client.post(
                f"{BASE}/resolve",
                json={"razonSocial": "Carrefour"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["id"] == regla["id"]

    async def test_should_return_no_match_when_no_regla_found(self, client, auth_headers):
        with patch(f"{REGLA_REPO}.resolve_regla", new_callable=AsyncMock, return_value=None):
            resp = await client.post(
                f"{BASE}/resolve",
                json={"razonSocial": "Unknown merchant"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.json() == {"match": False}

    async def test_should_require_auth(self, client):
        resp = await client.post(f"{BASE}/resolve", json={"razonSocial": "X"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /reglas/{id}
# ---------------------------------------------------------------------------

class TestPatchRegla:
    async def test_should_update_regla(self, client, auth_headers):
        updated = make_regla_dict()
        with patch(f"{REGLA_REPO}.update_regla", new_callable=AsyncMock, return_value=updated):
            resp = await client.patch(
                f"{BASE}/200",
                json={"idSubcategoria": "10"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["id"] == updated["id"]

    async def test_should_return_404_when_not_found(self, client, auth_headers):
        with patch(f"{REGLA_REPO}.update_regla", new_callable=AsyncMock, return_value=None):
            resp = await client.patch(
                f"{BASE}/999",
                json={"idSubcategoria": "10"},
                headers=auth_headers,
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /reglas/{id}
# ---------------------------------------------------------------------------

class TestDeleteRegla:
    async def test_should_delete_and_return_confirmation(self, client, auth_headers):
        with patch(f"{REGLA_REPO}.delete_regla", new_callable=AsyncMock, return_value=True):
            resp = await client.delete(f"{BASE}/200", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True
        assert body["id"] == "200"

    async def test_should_return_404_when_not_found(self, client, auth_headers):
        with patch(f"{REGLA_REPO}.delete_regla", new_callable=AsyncMock, return_value=False):
            resp = await client.delete(f"{BASE}/999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_should_require_auth(self, client):
        resp = await client.delete(f"{BASE}/1")
        assert resp.status_code == 401
