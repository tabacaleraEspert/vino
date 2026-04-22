"""
Integration tests for:
- /api/v1/categorias        (GET, POST, PATCH, DELETE)
- /api/v1/categorias/{id}/subcategorias  (POST)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import make_categoria_dict, make_subcategoria_dict

pytestmark = pytest.mark.anyio

BASE = "/api/v1/categorias"
CAT_REPO = "app.api.v1.categorias"


# ---------------------------------------------------------------------------
# GET /categorias
# ---------------------------------------------------------------------------

class TestListCategorias:
    async def test_should_return_list_of_categorias(self, client, auth_headers):
        cats = [make_categoria_dict(1, "Alimentacion"), make_categoria_dict(2, "Transporte")]
        with patch(f"{CAT_REPO}.list_categorias", new_callable=AsyncMock, return_value=cats):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_should_return_empty_list_when_no_categorias(self, client, auth_headers):
        with patch(f"{CAT_REPO}.list_categorias", new_callable=AsyncMock, return_value=[]):
            resp = await client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_should_require_auth(self, client):
        resp = await client.get(BASE)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /categorias
# ---------------------------------------------------------------------------

class TestCreateCategoria:
    async def test_should_create_categoria_with_required_fields(self, client, auth_headers):
        cat = make_categoria_dict()
        with patch(f"{CAT_REPO}.create_categoria", new_callable=AsyncMock, return_value=cat):
            resp = await client.post(BASE, json={"name": "Alimentacion"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == cat["id"]

    async def test_should_create_categoria_with_custom_icon_and_color(self, client, auth_headers):
        cat = make_categoria_dict()
        with patch(f"{CAT_REPO}.create_categoria", new_callable=AsyncMock, return_value=cat) as mock_create:
            await client.post(
                BASE,
                json={"name": "Salud", "icon": "💊", "color": "#ff0000"},
                headers=auth_headers,
            )
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["icon"] == "💊"
        assert call_kwargs["color"] == "#ff0000"

    async def test_should_create_categoria_with_subcategories(self, client, auth_headers):
        cat = make_categoria_dict()
        sub = make_subcategoria_dict()
        with (
            patch(f"{CAT_REPO}.create_categoria", new_callable=AsyncMock, return_value=cat),
            patch(f"{CAT_REPO}.create_subcategoria", new_callable=AsyncMock, return_value=sub) as mock_sub,
        ):
            resp = await client.post(
                BASE,
                json={"name": "Alimentacion", "subcategories": [{"name": "Supermercado"}]},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        mock_sub.assert_awaited_once()

    async def test_should_require_auth(self, client):
        resp = await client.post(BASE, json={"name": "X"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /categorias/{id}
# ---------------------------------------------------------------------------

class TestPatchCategoria:
    async def test_should_update_nombre(self, client, auth_headers):
        updated = make_categoria_dict()
        updated["nombre"] = "Comida"
        with patch(f"{CAT_REPO}.update_categoria", new_callable=AsyncMock, return_value=updated):
            resp = await client.patch(f"{BASE}/1", json={"name": "Comida"}, headers=auth_headers)
        assert resp.status_code == 200

    async def test_should_return_404_when_categoria_not_found(self, client, auth_headers):
        with patch(f"{CAT_REPO}.update_categoria", new_callable=AsyncMock, return_value=None):
            resp = await client.patch(f"{BASE}/999", json={"name": "X"}, headers=auth_headers)
        assert resp.status_code == 404

    async def test_should_return_existing_when_no_patch_fields(self, client, auth_headers):
        cat = make_categoria_dict()
        with patch(f"{CAT_REPO}.get_categoria", new_callable=AsyncMock, return_value=cat):
            resp = await client.patch(f"{BASE}/1", json={}, headers=auth_headers)
        assert resp.status_code == 200

    async def test_should_return_404_when_no_patch_and_not_found(self, client, auth_headers):
        with patch(f"{CAT_REPO}.get_categoria", new_callable=AsyncMock, return_value=None):
            resp = await client.patch(f"{BASE}/999", json={}, headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /categorias/{id}
# ---------------------------------------------------------------------------

class TestDeleteCategoria:
    async def test_should_delete_and_return_confirmation(self, client, auth_headers):
        with patch(f"{CAT_REPO}.delete_categoria", new_callable=AsyncMock, return_value=True):
            resp = await client.delete(f"{BASE}/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    async def test_should_return_404_when_not_found(self, client, auth_headers):
        with patch(f"{CAT_REPO}.delete_categoria", new_callable=AsyncMock, return_value=False):
            resp = await client.delete(f"{BASE}/999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_should_require_auth(self, client):
        resp = await client.delete(f"{BASE}/1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /categorias/{id}/subcategorias
# ---------------------------------------------------------------------------

class TestCreateSubcategoria:
    async def test_should_create_subcategoria_under_categoria(self, client, auth_headers):
        sub = make_subcategoria_dict(sub_id=10, categoria_id=1)
        with patch(f"{CAT_REPO}.create_subcategoria", new_callable=AsyncMock, return_value=sub):
            resp = await client.post(
                f"{BASE}/1/subcategorias",
                json={"name": "Supermercado"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == sub["id"]
        assert body["categoryId"] == sub["categoria_id"]

    async def test_should_return_400_for_empty_name(self, client, auth_headers):
        resp = await client.post(
            f"{BASE}/1/subcategorias",
            json={"name": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "vacío" in resp.json()["detail"]

    async def test_should_require_auth(self, client):
        resp = await client.post(f"{BASE}/1/subcategorias", json={"name": "X"})
        assert resp.status_code == 401
