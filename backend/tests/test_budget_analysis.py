"""
Tests for budget analysis service and endpoints.

Service tests: pure logic with mocked repo calls.
Endpoint tests: full HTTP via test client.
"""
from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import make_user_dict

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_USER_ID = 42

_PRESUPUESTOS = [
    {"id": 1, "categoria_id": "1", "categoria_nombre": "Alimentacion", "subcategoria_id": "", "subcategoria_nombre": "", "monto": 100000, "mes_anio": "04/26"},
    {"id": 2, "categoria_id": "2", "categoria_nombre": "Transporte", "subcategoria_id": "", "subcategoria_nombre": "", "monto": 50000, "mes_anio": "04/26"},
    {"id": 3, "categoria_id": "3", "categoria_nombre": "Entretenimiento", "subcategoria_id": "", "subcategoria_nombre": "", "monto": 30000, "mes_anio": "04/26"},
]

_MOVIMIENTOS = [
    # Alimentacion: 85000 (85% of 100000)
    {"monto": 45000, "Id_Categoria": 1, "idCategoria": "1", "categoria": "Alimentacion", "Nombre_Categoria": "Alimentacion"},
    {"monto": 40000, "Id_Categoria": 1, "idCategoria": "1", "categoria": "Alimentacion", "Nombre_Categoria": "Alimentacion"},
    # Transporte: 55000 (110% of 50000 — over budget)
    {"monto": 30000, "Id_Categoria": 2, "idCategoria": "2", "categoria": "Transporte", "Nombre_Categoria": "Transporte"},
    {"monto": 25000, "Id_Categoria": 2, "idCategoria": "2", "categoria": "Transporte", "Nombre_Categoria": "Transporte"},
    # Entretenimiento: 10000 (33% of 30000)
    {"monto": 10000, "Id_Categoria": 3, "idCategoria": "3", "categoria": "Entretenimiento", "Nombre_Categoria": "Entretenimiento"},
    # Salud: 20000 (no budget)
    {"monto": 20000, "Id_Categoria": 4, "idCategoria": "4", "categoria": "Salud", "Nombre_Categoria": "Salud"},
]


def _patch_repos():
    return [
        patch(
            "app.services.presupuesto_analysis.list_presupuestos",
            new_callable=AsyncMock,
            return_value=_PRESUPUESTOS,
        ),
        patch(
            "app.services.presupuesto_analysis.list_movimientos",
            new_callable=AsyncMock,
            return_value=(_MOVIMIENTOS, len(_MOVIMIENTOS)),
        ),
    ]


async def _with_patches(patches, coro):
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        return await coro


# ===========================================================================
# Service: budget_vs_actual
# ===========================================================================

class TestBudgetVsActual:
    async def test_returns_correct_totals(self):
        from app.services.presupuesto_analysis import budget_vs_actual
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = await budget_vs_actual(db, _USER_ID, "2026-04")

        assert result["total_presupuesto"] == 180000
        # total_gastado = 85000 (Alim) + 55000 (Trans) + 10000 (Entret) + 20000 (Salud)
        assert result["total_gastado"] == 170000
        assert result["total_restante"] == 10000

    async def test_returns_per_category_breakdown(self):
        from app.services.presupuesto_analysis import budget_vs_actual
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = await budget_vs_actual(db, _USER_ID, "2026-04")

        cats = {c["categoria"]: c for c in result["categorias"]}
        assert "Alimentacion" in cats
        assert cats["Alimentacion"]["presupuesto"] == 100000
        assert cats["Alimentacion"]["gastado"] == 85000
        assert cats["Alimentacion"]["pct_usado"] == 85.0

    async def test_detects_over_budget(self):
        from app.services.presupuesto_analysis import budget_vs_actual
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = await budget_vs_actual(db, _USER_ID, "2026-04")

        cats = {c["categoria"]: c for c in result["categorias"]}
        assert cats["Transporte"]["pct_usado"] == 110.0
        assert cats["Transporte"]["restante"] == -5000

    async def test_includes_categories_without_budget(self):
        from app.services.presupuesto_analysis import budget_vs_actual
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = await budget_vs_actual(db, _USER_ID, "2026-04")

        cats = {c["categoria"]: c for c in result["categorias"]}
        assert "Salud" in cats
        assert cats["Salud"]["presupuesto"] == 0
        assert cats["Salud"]["gastado"] == 20000

    async def test_has_days_info(self):
        from app.services.presupuesto_analysis import budget_vs_actual
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = await budget_vs_actual(db, _USER_ID, "2026-04")

        assert "dias_transcurridos" in result
        assert "dias_restantes" in result
        assert result["dias_transcurridos"] + result["dias_restantes"] == 30  # April


# ===========================================================================
# Service: generate_suggestions
# ===========================================================================

class TestGenerateSuggestions:
    async def test_generates_alert_for_over_budget(self):
        from app.services.presupuesto_analysis import generate_suggestions
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            suggestions = await generate_suggestions(db, _USER_ID, "2026-04")

        alertas = [s for s in suggestions if s["tipo"] == "alerta"]
        transport_alerts = [s for s in alertas if s["categoria"] == "Transporte"]
        assert len(transport_alerts) >= 1
        assert "pasaste" in transport_alerts[0]["mensaje"].lower() or "superaste" in transport_alerts[0]["mensaje"].lower()

    async def test_generates_warning_for_near_limit(self):
        from app.services.presupuesto_analysis import generate_suggestions
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            suggestions = await generate_suggestions(db, _USER_ID, "2026-04")

        # Alimentacion is at 85% — should have a warning
        warnings = [s for s in suggestions if s["tipo"] == "advertencia" and s["categoria"] == "Alimentacion"]
        assert len(warnings) >= 1

    async def test_generates_info_for_no_budget(self):
        from app.services.presupuesto_analysis import generate_suggestions
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            suggestions = await generate_suggestions(db, _USER_ID, "2026-04")

        info = [s for s in suggestions if s["tipo"] == "info" and s["categoria"] == "Salud"]
        assert len(info) >= 1
        assert "sin presupuesto" in info[0]["mensaje"].lower()

    async def test_sorted_by_priority(self):
        from app.services.presupuesto_analysis import generate_suggestions
        db = AsyncMock()
        patches = _patch_repos()
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            suggestions = await generate_suggestions(db, _USER_ID, "2026-04")

        if len(suggestions) >= 2:
            priority = {"alerta": 0, "advertencia": 1, "info": 2, "positivo": 3}
            for i in range(len(suggestions) - 1):
                assert priority.get(suggestions[i]["tipo"], 9) <= priority.get(suggestions[i + 1]["tipo"], 9)

    async def test_returns_empty_when_no_data(self):
        from app.services.presupuesto_analysis import generate_suggestions
        db = AsyncMock()
        with patch(
            "app.services.presupuesto_analysis.list_presupuestos",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.presupuesto_analysis.list_movimientos",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            suggestions = await generate_suggestions(db, _USER_ID, "2026-04")

        assert suggestions == []


# ===========================================================================
# Endpoint: /views/budget/status
# ===========================================================================

class TestBudgetStatusEndpoint:
    async def test_returns_401_without_auth(self, client):
        resp = await client.get("/api/v1/views/budget/status?period=2026-04")
        assert resp.status_code == 401

    async def test_returns_400_with_bad_period(self, client, auth_headers):
        resp = await client.get(
            "/api/v1/views/budget/status?period=bad",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_returns_budget_status(self, client, auth_headers):
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.get(
                "/api/v1/views/budget/status?period=2026-04",
                headers=auth_headers,
            ),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_presupuesto" in body
        assert "total_gastado" in body
        assert "categorias" in body
        assert isinstance(body["categorias"], list)


# ===========================================================================
# Endpoint: /views/budget/suggestions
# ===========================================================================

class TestBudgetSuggestionsEndpoint:
    async def test_returns_401_without_auth(self, client):
        resp = await client.get("/api/v1/views/budget/suggestions?period=2026-04")
        assert resp.status_code == 401

    async def test_returns_suggestions(self, client, auth_headers):
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.get(
                "/api/v1/views/budget/suggestions?period=2026-04",
                headers=auth_headers,
            ),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "suggestions" in body
        assert isinstance(body["suggestions"], list)
        assert body["period"] == "2026-04"

    async def test_each_suggestion_has_required_fields(self, client, auth_headers):
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.get(
                "/api/v1/views/budget/suggestions?period=2026-04",
                headers=auth_headers,
            ),
        )
        for s in resp.json()["suggestions"]:
            assert "tipo" in s
            assert "categoria" in s
            assert "mensaje" in s
            assert s["tipo"] in ("alerta", "advertencia", "info", "positivo")
