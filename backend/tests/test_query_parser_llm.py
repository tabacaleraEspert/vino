"""
Integration tests for parse_query — calls OpenAI for real.

Run with:  pytest tests/test_query_parser_llm.py -m llm
Skip with: pytest -m "not llm"

Validates that the LLM prompt correctly extracts periodo, metrica,
categorias from real user messages.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.query_parser import Metrica, parse_query

pytestmark = [pytest.mark.anyio, pytest.mark.llm]

REF = date(2026, 4, 28)

CATALOGO = [
    {"id": 1, "nombre": "Alimentacion"},
    {"id": 2, "nombre": "Transporte"},
    {"id": 3, "nombre": "Entretenimiento"},
    {"id": 4, "nombre": "Salud"},
    {"id": 5, "nombre": "Ropa"},
    {"id": 6, "nombre": "Otros"},
    {"id": 7, "nombre": "Vivienda"},
    {"id": 8, "nombre": "Educacion"},
]


# ===========================================================================
# TOTAL queries
# ===========================================================================

class TestParseTotal:
    async def test_cuanto_gaste_este_mes(self):
        p = await parse_query("Cuánto gasté este mes?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.TOTAL
        assert p.from_date == date(2026, 4, 1)

    async def test_cuanto_gaste_en_comida(self):
        p = await parse_query("Cuánto gasté en comida este mes?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.TOTAL
        assert p.categoria_ids == [1]  # Alimentacion

    async def test_cuanto_gaste_ayer(self):
        p = await parse_query("Cuánto gasté ayer?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.TOTAL
        assert p.from_date == date(2026, 4, 27)
        assert p.to_date == date(2026, 4, 27)

    async def test_cuanto_gaste_esta_semana(self):
        p = await parse_query("Cuánto gasté esta semana?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.TOTAL
        assert p.from_date == date(2026, 4, 27)  # Monday

    async def test_cuanto_en_transporte_mes_pasado(self):
        p = await parse_query("Cuánto gasté en transporte el mes pasado?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.TOTAL
        assert p.categoria_ids == [2]
        assert p.from_date == date(2026, 3, 1)


# ===========================================================================
# RESUMEN queries
# ===========================================================================

class TestParseResumen:
    async def test_como_vengo(self):
        p = await parse_query("Cómo vengo este mes?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.RESUMEN

    async def test_dame_un_resumen(self):
        p = await parse_query("Dame un resumen del mes", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.RESUMEN

    async def test_gaste_plata_ayer(self):
        """The production failure case."""
        p = await parse_query("Hola gaste plata ayer?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.RESUMEN
        assert p.from_date == date(2026, 4, 27)

    async def test_como_me_fue_esta_semana(self):
        p = await parse_query("Cómo me fue esta semana?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.RESUMEN


# ===========================================================================
# TOP_N / PORCENTAJE queries
# ===========================================================================

class TestParseTopN:
    async def test_en_que_gasto_mas(self):
        p = await parse_query("En qué categoría gasto más?", CATALOGO, ref_date=REF)
        assert p.metrica in (Metrica.TOP_N, Metrica.PORCENTAJE)

    async def test_top_3_categorias(self):
        p = await parse_query("Top 3 categorías de gasto este mes", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.TOP_N
        assert p.top_n == 3


# ===========================================================================
# MAYOR / MENOR queries
# ===========================================================================

class TestParseMayorMenor:
    async def test_mayor_gasto_del_mes(self):
        p = await parse_query("Cuál fue mi mayor gasto del mes?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.MAYOR

    async def test_gasto_mas_grande_de_la_semana(self):
        p = await parse_query("Cuál fue el gasto más grande de la semana?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.MAYOR

    async def test_menor_gasto(self):
        p = await parse_query("Cuál fue mi menor gasto?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.MENOR


# ===========================================================================
# CONTEO queries
# ===========================================================================

class TestParseConteo:
    async def test_cuantas_veces_comi_afuera(self):
        p = await parse_query("Cuántas veces comí afuera este mes?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.CONTEO
        assert p.categoria_ids == [1]

    async def test_cuantos_gastos_hice(self):
        p = await parse_query("Cuántos gastos hice este mes?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.CONTEO


# ===========================================================================
# PROMEDIO queries
# ===========================================================================

class TestParsePromedio:
    async def test_ticket_promedio(self):
        p = await parse_query("Cuál es mi ticket promedio?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.PROMEDIO

    async def test_cuanto_gasto_en_promedio_en_transporte(self):
        p = await parse_query("Cuánto gasto en promedio en transporte?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.PROMEDIO
        assert p.categoria_ids == [2]


# ===========================================================================
# LISTADO queries
# ===========================================================================

class TestParseListado:
    async def test_ultimos_gastos(self):
        p = await parse_query("Mostrame mis últimos gastos", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.LISTADO

    async def test_ultimos_10_en_transporte(self):
        p = await parse_query("Mostrame los últimos 10 gastos en transporte", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.LISTADO
        assert p.categoria_ids == [2]
        assert p.top_n == 10


# ===========================================================================
# COMPARAR queries
# ===========================================================================

class TestParseComparar:
    async def test_compara_este_mes_vs_anterior(self):
        p = await parse_query("Compará este mes con el anterior", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.COMPARAR
        assert p.from_date == date(2026, 4, 1)
        assert p.compare_from_date == date(2026, 3, 1)
        assert p.compare_to_date == date(2026, 3, 31)

    async def test_compara_categoria_especifica(self):
        p = await parse_query(
            "Compará cuánto gasté en comida este mes vs el mes pasado",
            CATALOGO, ref_date=REF,
        )
        assert p.metrica == Metrica.COMPARAR
        assert p.categoria_ids == [1]
        assert p.compare_from_date is not None

    async def test_gaste_mas_o_menos(self):
        p = await parse_query("Gasté más o menos que el mes pasado?", CATALOGO, ref_date=REF)
        assert p.metrica == Metrica.COMPARAR
        assert p.compare_from_date == date(2026, 3, 1)

    async def test_diferencia_semanas(self):
        p = await parse_query(
            "Diferencia entre esta semana y la pasada en transporte",
            CATALOGO, ref_date=REF,
        )
        assert p.metrica == Metrica.COMPARAR
        assert p.categoria_ids == [2]
        assert p.compare_from_date is not None

    async def test_porcentaje_diferencia_comida(self):
        p = await parse_query(
            "Cuál es la diferencia porcentual en alimentación entre este mes y el anterior?",
            CATALOGO, ref_date=REF,
        )
        assert p.metrica == Metrica.COMPARAR
        assert p.categoria_ids == [1]
