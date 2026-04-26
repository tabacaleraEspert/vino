"""
Tests for purchase advisor service and endpoint.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings

pytestmark = pytest.mark.anyio

MASTER_HEADERS = {"X-Master-Key": settings.MASTER_KEY}

# Mock budget analysis data
_ANALYSIS = {
    "period": "2026-04",
    "moneda": "ARS",
    "dias_transcurridos": 24,
    "dias_restantes": 6,
    "total_presupuesto": 500000,
    "total_gastado": 350000,
    "total_restante": 150000,
    "pct_usado_global": 70.0,
    "categorias": [
        {"categoria_id": "1", "categoria": "Ropa", "presupuesto": 80000, "gastado": 30000, "restante": 50000, "pct_usado": 37.5},
        {"categoria_id": "2", "categoria": "Alimentacion", "presupuesto": 200000, "gastado": 180000, "restante": 20000, "pct_usado": 90.0},
        {"categoria_id": "3", "categoria": "Transporte", "presupuesto": 100000, "gastado": 110000, "restante": -10000, "pct_usado": 110.0},
    ],
}

_ANALYSIS_EMPTY = {
    "period": "2026-04",
    "moneda": "ARS",
    "dias_transcurridos": 24,
    "dias_restantes": 6,
    "total_presupuesto": 0,
    "total_gastado": 0,
    "total_restante": 0,
    "pct_usado_global": 0,
    "categorias": [],
}


def _patch_extract(item="remera", monto=60000, categoria="Ropa"):
    return patch(
        "app.services.purchase_advisor._extract_purchase",
        new_callable=AsyncMock,
        return_value={"item": item, "monto": monto, "categoria_probable": categoria},
    )


def _patch_analysis(analysis=_ANALYSIS):
    return patch(
        "app.services.purchase_advisor.budget_vs_actual",
        new_callable=AsyncMock,
        return_value=analysis,
    )


# ===========================================================================
# Service tests
# ===========================================================================

class TestPurchaseAdvisor:
    async def test_can_afford_returns_positive(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract("remera", 40000, "Ropa"), _patch_analysis():
            result = await advise_purchase(db, 1, "Puedo comprarme una remera de 40k?", "Davor")
        assert "podes" in result.lower() or "si" in result.lower()

    async def test_over_budget_returns_warning(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract("uber", 5000, "Transporte"), _patch_analysis():
            result = await advise_purchase(db, 1, "Puedo tomarme un uber de 5k?", "Davor")
        assert "pasado" in result.lower() or "excedido" in result.lower()

    async def test_would_exceed_budget(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract("remera", 60000, "Ropa"), _patch_analysis():
            # 60k > 50k remaining in Ropa
            result = await advise_purchase(db, 1, "Puedo comprarme una remera de 60k?", "Davor")
        assert "pasaria" in result.lower() or "presupuesto" in result.lower()

    async def test_no_budgets_returns_message(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract("remera", 60000, "Ropa"), _patch_analysis(_ANALYSIS_EMPTY):
            result = await advise_purchase(db, 1, "Puedo comprarme una remera?", "Davor")
        assert "presupuesto" in result.lower()

    async def test_no_item_extracted(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract(None, None, None), _patch_analysis():
            result = await advise_purchase(db, 1, "hola", "Davor")
        assert "no entendi" in result.lower() or "decime" in result.lower()

    async def test_no_amount_asks_for_price(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract("zapatillas", None, "Ropa"), _patch_analysis():
            result = await advise_purchase(db, 1, "Quiero comprarme unas zapatillas", "Davor")
        assert "cuanto" in result.lower() or "sale" in result.lower()

    async def test_unknown_category_uses_total(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract("drone", 200000, "Tecnologia"), _patch_analysis():
            # "Tecnologia" is not in the budget categories
            result = await advise_purchase(db, 1, "Puedo comprarme un drone de 200k?", "Davor")
        assert "presupuesto" in result.lower()


# ===========================================================================
# Endpoint tests
# ===========================================================================

class TestSuggestPurchaseEndpoint:
    async def test_returns_401_without_master_key(self, client):
        resp = await client.post(
            "/api/v1/whatsapp/suggest-purchase",
            json={"user_id": 1, "message": "test"},
        )
        assert resp.status_code == 401

    async def test_returns_reply(self, client):
        with _patch_extract("remera", 40000, "Ropa"), _patch_analysis():
            resp = await client.post(
                "/api/v1/whatsapp/suggest-purchase",
                json={"user_id": 1, "message": "Puedo comprarme una remera de 40k?", "user_name": "Davor"},
                headers=MASTER_HEADERS,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "reply" in body
        assert len(body["reply"]) > 10

    async def test_reply_is_string(self, client):
        with _patch_extract("remera", 40000, "Ropa"), _patch_analysis():
            resp = await client.post(
                "/api/v1/whatsapp/suggest-purchase",
                json={"user_id": 1, "message": "Puedo comprarme una remera de 40k?"},
                headers=MASTER_HEADERS,
            )
        assert isinstance(resp.json()["reply"], str)
