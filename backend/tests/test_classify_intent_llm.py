"""
Integration tests for classify_intent — calls OpenAI for real.

Run with:  pytest tests/test_classify_intent_llm.py -m llm
Skip with: pytest -m "not llm"

These validate that the prompt correctly classifies real user messages
into DATA, QUERY, SUGERENCIAS, or OTHER.
"""
from __future__ import annotations

import pytest

from app.services.whatsapp_intake import Intent, classify_intent

pytestmark = [pytest.mark.anyio, pytest.mark.llm]


# ===========================================================================
# DATA — registrar un gasto/ingreso (15 tests)
# ===========================================================================


class TestClassifyData:
    """Messages that register an expense or income → DATA."""

    async def test_gaste_con_monto_y_lugar(self):
        assert await classify_intent("Gasté 5000 en Carrefour") == Intent.DATA

    async def test_almorce_con_monto(self):
        assert await classify_intent("Almorcé 3500") == Intent.DATA

    async def test_pague_la_luz(self):
        assert await classify_intent("Pagué la luz 12000") == Intent.DATA

    async def test_taxi_con_monto(self):
        assert await classify_intent("Taxi 2500") == Intent.DATA

    async def test_slang_lucas(self):
        assert await classify_intent("300 lucas en Nike") == Intent.DATA

    async def test_slang_k(self):
        assert await classify_intent("50k en ropa") == Intent.DATA

    async def test_uber_con_monto(self):
        assert await classify_intent("Uber hoy 1800") == Intent.DATA

    async def test_nafta_con_debito(self):
        assert await classify_intent("Nafta 15000 con débito") == Intent.DATA

    async def test_quiero_cargar_gasto(self):
        assert await classify_intent("Quiero cargar un gasto de 8000 en farmacia") == Intent.DATA

    async def test_cene_con_amigos(self):
        assert await classify_intent("Cené con amigos 12000") == Intent.DATA

    async def test_compre_algo(self):
        assert await classify_intent("Me compré unas zapatillas 45000") == Intent.DATA

    async def test_pago_transferencia(self):
        assert await classify_intent("Le transferí 5000 a Juan") == Intent.DATA

    async def test_slang_palo(self):
        assert await classify_intent("1 palo en el dentista") == Intent.DATA

    async def test_delivery_con_monto(self):
        assert await classify_intent("Pedí delivery 4500") == Intent.DATA

    async def test_supermercado_informal(self):
        assert await classify_intent("Super 23000 con tarjeta") == Intent.DATA


# ===========================================================================
# QUERY — preguntas sobre finanzas (10 tests)
# ===========================================================================


class TestClassifyQuery:
    """Messages that ask about financial state → QUERY."""

    async def test_cuanto_gaste_este_mes(self):
        assert await classify_intent("Cuánto gasté este mes?") == Intent.QUERY

    async def test_gaste_plata_ayer(self):
        """The exact message that failed in production."""
        assert await classify_intent("Hola gaste plata ayer?") == Intent.QUERY

    async def test_en_que_gasto_mas(self):
        assert await classify_intent("En qué categoría gasto más?") == Intent.QUERY

    async def test_como_vengo_este_mes(self):
        assert await classify_intent("Cómo vengo este mes?") == Intent.QUERY

    async def test_dame_un_resumen(self):
        assert await classify_intent("Dame un resumen del mes") == Intent.QUERY

    async def test_ultimo_gasto(self):
        assert await classify_intent("Cuál fue mi último gasto?") == Intent.QUERY

    async def test_como_viene_presupuesto(self):
        assert await classify_intent("Cómo viene mi presupuesto?") == Intent.QUERY

    async def test_que_categorias_tengo(self):
        assert await classify_intent("Qué categorías tengo?") == Intent.QUERY

    async def test_cuanto_gaste_en_comida(self):
        assert await classify_intent("Cuánto gasté en comida esta semana?") == Intent.QUERY

    async def test_resumen_semanal(self):
        assert await classify_intent("Cómo me fue esta semana?") == Intent.QUERY


# ===========================================================================
# SUGERENCIAS — consejo o evaluación de compra futura (10 tests)
# ===========================================================================


class TestClassifySugerencias:
    """Messages asking for purchase advice → SUGERENCIAS."""

    async def test_puedo_comprarme_zapatillas(self):
        assert await classify_intent("Puedo comprarme unas zapatillas de 80k?") == Intent.SUGERENCIAS

    async def test_me_alcanza_para_salir(self):
        assert await classify_intent("Me alcanza para salir a comer este finde?") == Intent.SUGERENCIAS

    async def test_me_conviene_comprar(self):
        assert await classify_intent("Me conviene comprar esto?") == Intent.SUGERENCIAS

    async def test_dame_sugerencias(self):
        assert await classify_intent("Dame sugerencias para ahorrar") == Intent.SUGERENCIAS

    async def test_es_caro(self):
        assert await classify_intent("Es caro 50k por una remera?") == Intent.SUGERENCIAS

    async def test_puedo_gastar_en_ropa(self):
        assert await classify_intent("Puedo gastar 30k en ropa este mes?") == Intent.SUGERENCIAS

    async def test_me_da_para_uber(self):
        assert await classify_intent("Me da el presupuesto para tomarme un Uber?") == Intent.SUGERENCIAS

    async def test_deberia_comprar(self):
        assert await classify_intent("Debería comprarme un monitor nuevo?") == Intent.SUGERENCIAS

    async def test_vale_la_pena(self):
        assert await classify_intent("Vale la pena pagar 120k por unas zapas?") == Intent.SUGERENCIAS

    async def test_puedo_permitirme(self):
        assert await classify_intent("Me puedo permitir un viaje este mes?") == Intent.SUGERENCIAS
