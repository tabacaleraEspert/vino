"""
Tests for purchase advisor service and endpoint.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.core.config import settings

pytestmark = pytest.mark.anyio

MASTER_HEADERS = {"X-Master-Key": settings.MASTER_KEY}

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
        return_value={"item": item, "monto": monto, "categoria_probable": categoria, "es_lugar": False, "lugar_nombre": None},
    )


def _patch_analysis(analysis=_ANALYSIS):
    return patch(
        "app.services.purchase_advisor.budget_vs_actual",
        new_callable=AsyncMock,
        return_value=analysis,
    )


def _patch_metrics():
    """Mock compute_category_metrics to avoid DB calls."""
    from app.services.smart_suggestions import CategoryMetrics
    mock_metrics = CategoryMetrics(
        categoria_id=1, categoria_nombre="Ropa", presupuesto=80000,
        gastado=30000, restante=50000, pct_usado=37.5,
        avg_ticket=15000, min_ticket=5000, max_ticket=40000,
        tx_count=5, trend_vs_last_month=10.0,
    )
    return patch(
        "app.services.purchase_advisor.compute_category_metrics",
        new_callable=AsyncMock,
        return_value=mock_metrics,
    )


def _patch_gpt_advice(reply="Sí, podés comprarlo. Te queda margen."):
    """Mock the final GPT advice generation."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = reply
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return patch(
        "app.services.purchase_advisor._get_client",
        return_value=mock_client,
    )


class TestPurchaseAdvisor:
    async def test_returns_string(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract("remera", 40000, "Ropa"), _patch_analysis(), _patch_metrics(), _patch_gpt_advice("Sí dale, te queda presupuesto"):
            result = await advise_purchase(db, 1, "Puedo comprarme una remera de 40k?", "Davor")
        assert isinstance(result, str)
        assert len(result) > 5

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
        assert "no entend" in result.lower() or "decime" in result.lower()

    async def test_with_amount_returns_advice(self):
        from app.services.purchase_advisor import advise_purchase
        db = AsyncMock()
        with _patch_extract("remera", 40000, "Ropa"), _patch_analysis(), _patch_metrics(), _patch_gpt_advice("Podés, te queda $50k en Ropa"):
            result = await advise_purchase(db, 1, "Puedo comprarme una remera de 40k?", "Davor")
        assert "50k" in result or "podés" in result.lower() or "ropa" in result.lower()


class TestSuggestPurchaseEndpoint:
    async def test_returns_401_without_master_key(self, client):
        resp = await client.post(
            "/api/v1/whatsapp/suggest-purchase",
            json={"user_id": 1, "message": "test"},
        )
        assert resp.status_code == 401

    async def test_returns_reply(self, client):
        with _patch_extract("remera", 40000, "Ropa"), _patch_analysis(), _patch_metrics(), _patch_gpt_advice("Dale tranqui"):
            resp = await client.post(
                "/api/v1/whatsapp/suggest-purchase",
                json={"user_id": 1, "message": "Puedo comprarme una remera de 40k?", "user_name": "Davor"},
                headers=MASTER_HEADERS,
            )
        assert resp.status_code == 200
        assert "reply" in resp.json()

    async def test_reply_is_string(self, client):
        with _patch_extract("remera", 40000, "Ropa"), _patch_analysis(), _patch_metrics(), _patch_gpt_advice("Sí"):
            resp = await client.post(
                "/api/v1/whatsapp/suggest-purchase",
                json={"user_id": 1, "message": "Puedo comprarme una remera de 40k?"},
                headers=MASTER_HEADERS,
            )
        assert isinstance(resp.json()["reply"], str)
