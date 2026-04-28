"""
Tests for the query pipeline: parse → execute → format.

Unit tests for:
- resolve_periodo (pure)
- match_categorias (pure)
- format_query_result (pure)
- execute_query (mocked repos)
- parse_query (mocked LLM)
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.services.query_parser import (
    Metrica,
    QueryParams,
    match_categorias,
    resolve_periodo,
)
from app.services.query_executor import QueryResult, execute_query
from app.services.query_formatter import format_query_result

pytestmark = pytest.mark.anyio


# ===========================================================================
# resolve_periodo — pure unit tests
# ===========================================================================

REF = date(2026, 4, 28)  # Tuesday


class TestResolvePeriodo:
    def test_hoy(self):
        f, t, label = resolve_periodo("hoy", REF)
        assert f == t == REF
        assert label == "hoy"

    def test_ayer(self):
        f, t, label = resolve_periodo("ayer", REF)
        assert f == t == date(2026, 4, 27)
        assert label == "ayer"

    def test_esta_semana(self):
        f, t, label = resolve_periodo("esta_semana", REF)
        assert f == date(2026, 4, 27)  # Monday
        assert t == REF

    def test_semana_pasada(self):
        f, t, label = resolve_periodo("semana_pasada", REF)
        assert f == date(2026, 4, 20)  # Previous Monday
        assert t == date(2026, 4, 26)  # Previous Sunday

    def test_este_mes(self):
        f, t, label = resolve_periodo("este_mes", REF)
        assert f == date(2026, 4, 1)
        assert t == REF

    def test_mes_pasado(self):
        f, t, label = resolve_periodo("mes_pasado", REF)
        assert f == date(2026, 3, 1)
        assert t == date(2026, 3, 31)

    def test_este_anio(self):
        f, t, label = resolve_periodo("este_anio", REF)
        assert f == date(2026, 1, 1)
        assert t == REF

    def test_ultimos_7_dias(self):
        f, t, label = resolve_periodo("ultimos_7_dias", REF)
        assert f == date(2026, 4, 22)
        assert t == REF

    def test_ultimos_30_dias(self):
        f, t, label = resolve_periodo("ultimos_30_dias", REF)
        assert f == date(2026, 3, 30)
        assert t == REF

    def test_unknown_falls_back_to_este_mes(self):
        f, t, label = resolve_periodo("banana", REF)
        assert f == date(2026, 4, 1)
        assert t == REF
        assert label == "este mes"


# ===========================================================================
# match_categorias — pure unit tests
# ===========================================================================

CATALOGO = [
    {"id": 1, "nombre": "Alimentacion"},
    {"id": 2, "nombre": "Transporte"},
    {"id": 3, "nombre": "Entretenimiento"},
    {"id": 4, "nombre": "Salud"},
    {"id": 5, "nombre": "Ropa"},
    {"id": 6, "nombre": "Otros"},
]


class TestMatchCategorias:
    def test_exact_match(self):
        assert match_categorias(["Alimentacion"], CATALOGO) == [1]

    def test_case_insensitive(self):
        assert match_categorias(["alimentacion"], CATALOGO) == [1]

    def test_substring_match(self):
        assert match_categorias(["comida"], CATALOGO) == []  # no match for "comida"

    def test_partial_match(self):
        assert match_categorias(["transport"], CATALOGO) == [2]

    def test_multiple(self):
        result = match_categorias(["alimentacion", "transporte"], CATALOGO)
        assert result == [1, 2]

    def test_empty_input(self):
        assert match_categorias([], CATALOGO) == []

    def test_no_match(self):
        assert match_categorias(["zapatos"], CATALOGO) == []


# ===========================================================================
# format_query_result — pure unit tests
# ===========================================================================


def _make_params(**kwargs) -> QueryParams:
    defaults = dict(
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 28),
        periodo_label="este mes",
        metrica=Metrica.TOTAL,
    )
    defaults.update(kwargs)
    return QueryParams(**defaults)


class TestFormatQueryResult:
    def test_format_total(self):
        r = QueryResult(
            metrica=Metrica.TOTAL,
            params=_make_params(metrica=Metrica.TOTAL),
            total=150000,
            conteo=42,
        )
        msg = format_query_result(r)
        assert "$150.000" in msg
        assert "42 gastos" in msg
        assert "este mes" in msg

    def test_format_total_with_category(self):
        r = QueryResult(
            metrica=Metrica.TOTAL,
            params=_make_params(metrica=Metrica.TOTAL, categorias=["comida"]),
            total=50000,
            conteo=15,
        )
        msg = format_query_result(r)
        assert "comida" in msg
        assert "$50.000" in msg

    def test_format_promedio(self):
        r = QueryResult(
            metrica=Metrica.PROMEDIO,
            params=_make_params(metrica=Metrica.PROMEDIO),
            promedio=3500,
            conteo=42,
            total=147000,
        )
        msg = format_query_result(r)
        assert "$3.500" in msg
        assert "promedio" in msg.lower()

    def test_format_conteo(self):
        r = QueryResult(
            metrica=Metrica.CONTEO,
            params=_make_params(metrica=Metrica.CONTEO),
            conteo=25,
            total=100000,
        )
        msg = format_query_result(r)
        assert "25" in msg
        assert "$100.000" in msg

    def test_format_mayor(self):
        r = QueryResult(
            metrica=Metrica.MAYOR,
            params=_make_params(metrica=Metrica.MAYOR),
            mayor=80000,
            movimientos=[{
                "monto": 80000, "descripcion": "Cena Fancy",
                "fecha": date(2026, 4, 15), "categoria_nombre": "Entretenimiento",
            }],
        )
        msg = format_query_result(r)
        assert "$80.000" in msg
        assert "Cena Fancy" in msg

    def test_format_top_n(self):
        r = QueryResult(
            metrica=Metrica.TOP_N,
            params=_make_params(metrica=Metrica.TOP_N),
            total=200000,
            por_categoria=[
                {"categoria": "Alimentacion", "total": 80000, "count": 20},
                {"categoria": "Transporte", "total": 60000, "count": 15},
                {"categoria": "Entretenimiento", "total": 40000, "count": 8},
            ],
        )
        msg = format_query_result(r)
        assert "Alimentacion" in msg
        assert "Transporte" in msg
        assert "1." in msg
        assert "2." in msg

    def test_format_porcentaje(self):
        r = QueryResult(
            metrica=Metrica.PORCENTAJE,
            params=_make_params(metrica=Metrica.PORCENTAJE),
            total=200000,
            por_categoria=[
                {"categoria": "Alimentacion", "total": 100000, "count": 20},
                {"categoria": "Transporte", "total": 60000, "count": 15},
            ],
        )
        msg = format_query_result(r)
        assert "50%" in msg  # 100k / 200k
        assert "30%" in msg  # 60k / 200k

    def test_format_listado(self):
        r = QueryResult(
            metrica=Metrica.LISTADO,
            params=_make_params(metrica=Metrica.LISTADO),
            movimientos=[
                {"monto": 5000, "descripcion": "Uber", "fecha": date(2026, 4, 27),
                 "categoria_nombre": "Transporte"},
                {"monto": 3000, "descripcion": "Cafe", "fecha": date(2026, 4, 26),
                 "categoria_nombre": "Alimentacion"},
            ],
            total_movimientos=50,
        )
        msg = format_query_result(r)
        assert "Uber" in msg
        assert "Cafe" in msg
        assert "48 más" in msg

    def test_format_resumen(self):
        r = QueryResult(
            metrica=Metrica.RESUMEN,
            params=_make_params(metrica=Metrica.RESUMEN),
            total=300000,
            conteo=60,
            promedio=5000,
            mayor=80000,
            por_categoria=[
                {"categoria": "Alimentacion", "total": 120000, "count": 30},
                {"categoria": "Transporte", "total": 80000, "count": 20},
            ],
        )
        msg = format_query_result(r)
        assert "Resumen" in msg
        assert "$300.000" in msg
        assert "60 gastos" in msg
        assert "$5.000" in msg  # promedio
        assert "$80.000" in msg  # mayor
        assert "Alimentacion" in msg
        assert "40%" in msg  # 120k / 300k

    def test_format_resumen_zero_gastos(self):
        r = QueryResult(
            metrica=Metrica.RESUMEN,
            params=_make_params(metrica=Metrica.RESUMEN),
            total=0,
            conteo=0,
        )
        msg = format_query_result(r)
        assert "$0" in msg
        assert "0 gastos" in msg


# ===========================================================================
# parse_query — mocked LLM
# ===========================================================================


class TestParseQueryMocked:
    """Test parse_query with mocked OpenAI responses."""

    def _mock_openai(self, json_content: str):
        mock_choice = type("C", (), {"message": type("M", (), {"content": json_content})()})()
        mock_response = type("R", (), {"choices": [mock_choice]})()
        return patch(
            "app.services.query_parser._get_openai_client",
            return_value=type("Client", (), {
                "chat": type("Chat", (), {
                    "completions": type("Completions", (), {
                        "create": AsyncMock(return_value=mock_response),
                    })(),
                })(),
            })(),
        )

    async def test_parses_total_este_mes(self):
        json_resp = '{"periodo":"este_mes","metrica":"total","categorias":[],"top_n":5,"moneda":"ARS"}'
        with self._mock_openai(json_resp):
            params = await parse_query("cuánto gasté este mes?", CATALOGO, ref_date=REF)
        assert params.metrica == Metrica.TOTAL
        assert params.from_date == date(2026, 4, 1)
        assert params.to_date == REF

    async def test_parses_category_filter(self):
        json_resp = '{"periodo":"este_mes","metrica":"total","categorias":["transporte"],"top_n":5,"moneda":"ARS"}'
        with self._mock_openai(json_resp):
            params = await parse_query("cuánto gasté en transporte?", CATALOGO, ref_date=REF)
        assert params.metrica == Metrica.TOTAL
        assert params.categoria_ids == [2]

    async def test_parses_resumen_ayer(self):
        json_resp = '{"periodo":"ayer","metrica":"resumen","categorias":[],"top_n":5,"moneda":"ARS"}'
        with self._mock_openai(json_resp):
            params = await parse_query("gasté plata ayer?", CATALOGO, ref_date=REF)
        assert params.metrica == Metrica.RESUMEN
        assert params.from_date == date(2026, 4, 27)
        assert params.to_date == date(2026, 4, 27)

    async def test_fallback_on_llm_error(self):
        with patch(
            "app.services.query_parser._get_openai_client",
            side_effect=Exception("API down"),
        ):
            params = await parse_query("algo", CATALOGO, ref_date=REF)
        # Fallback: resumen este mes
        assert params.metrica == Metrica.RESUMEN
        assert params.from_date == date(2026, 4, 1)

    async def test_unknown_metrica_falls_back_to_resumen(self):
        json_resp = '{"periodo":"este_mes","metrica":"BANANA","categorias":[],"top_n":5,"moneda":"ARS"}'
        with self._mock_openai(json_resp):
            params = await parse_query("algo raro", CATALOGO, ref_date=REF)
        assert params.metrica == Metrica.RESUMEN


# Need to import parse_query here (after CATALOGO is defined)
from app.services.query_parser import parse_query
