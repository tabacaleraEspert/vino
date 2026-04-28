"""
Parse a natural-language financial query into structured parameters.

Pipeline: raw message → LLM extraction → typed QueryParams.
This is step 1 of the query pipeline (parse → execute → format).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class Metrica(str, Enum):
    TOTAL = "total"
    PROMEDIO = "promedio"
    PORCENTAJE = "porcentaje"
    MAYOR = "mayor"
    MENOR = "menor"
    TOP_N = "top_n"
    CONTEO = "conteo"
    LISTADO = "listado"
    RESUMEN = "resumen"
    COMPARAR = "comparar"


@dataclass
class QueryParams:
    """Structured output from parsing a financial query."""
    from_date: date
    to_date: date
    periodo_label: str  # "hoy", "esta semana", "abril 2026", etc.
    metrica: Metrica
    categorias: list[str] = field(default_factory=list)  # nombres raw del usuario
    categoria_ids: list[int] = field(default_factory=list)  # resolved IDs
    top_n: int = 5
    moneda: str = "ARS"
    # For COMPARAR: second period to compare against
    compare_from_date: date | None = None
    compare_to_date: date | None = None
    compare_periodo_label: str = ""


# ---------------------------------------------------------------------------
# LLM prompt — focused only on extraction, not answering
# ---------------------------------------------------------------------------

_PARSE_SYSTEM_PROMPT = """\
Extraé los parámetros de una consulta financiera en español.
Respondé SOLO con JSON válido, sin texto adicional.

Campos a extraer:

"periodo": uno de: "hoy", "ayer", "esta_semana", "semana_pasada", \
"este_mes", "mes_pasado", "este_anio", "anio_pasado", "ultimos_7_dias", \
"ultimos_30_dias", "ultimos_3_meses", "todo"
  - Si no se menciona periodo, usá "este_mes".
  - "cómo vengo" / "cómo voy" = "este_mes"

"metrica": uno de: "total", "promedio", "porcentaje", "mayor", "menor", \
"top_n", "conteo", "listado", "resumen", "comparar"
  - "cuánto gasté" = "total"
  - "en qué gasté más" / "top categorías" = "top_n"
  - "cuántas veces" / "cuántos gastos" = "conteo"
  - "gasto más grande" / "mayor gasto" = "mayor"
  - "gasto más chico" / "menor gasto" = "menor"
  - "qué porcentaje" / "qué % va a" = "porcentaje"
  - "ticket promedio" / "cuánto gasto en promedio" = "promedio"
  - "últimos gastos" / "mostrame los gastos" = "listado"
  - "resumen" / "cómo vengo" / "cómo voy" / "dame un resumen" = "resumen"
  - "comparar", "diferencia entre", "vs", "contra", "respecto a", \
"más o menos que" = "comparar"
  - Si no queda claro, usá "resumen".

"categorias": lista de nombres de categorías mencionadas. \
Ej: ["comida", "transporte"]. Lista vacía si no menciona ninguna.

"top_n": número si pide "top N" o "las N categorías". Default 5.

"moneda": "ARS", "USD", o "EUR". Default "ARS".

"periodo_comparar": SOLO si metrica="comparar". El segundo periodo contra \
el que se compara. Mismos valores que "periodo". \
Si dice "este mes vs el anterior", periodo="este_mes", \
periodo_comparar="mes_pasado". Omitir si no es comparación.

Ejemplos:
- "Cuánto gasté en comida este mes?" → \
{"periodo":"este_mes","metrica":"total","categorias":["comida"],"top_n":5,"moneda":"ARS"}
- "Gasté plata ayer?" → \
{"periodo":"ayer","metrica":"resumen","categorias":[],"top_n":5,"moneda":"ARS"}
- "En qué categoría gasto más?" → \
{"periodo":"este_mes","metrica":"top_n","categorias":[],"top_n":5,"moneda":"ARS"}
- "Cuál fue mi mayor gasto de la semana?" → \
{"periodo":"esta_semana","metrica":"mayor","categorias":[],"top_n":5,"moneda":"ARS"}
- "Cómo vengo este mes?" → \
{"periodo":"este_mes","metrica":"resumen","categorias":[],"top_n":5,"moneda":"ARS"}
- "Cuántas veces comí afuera este mes?" → \
{"periodo":"este_mes","metrica":"conteo","categorias":["comida"],"top_n":5,"moneda":"ARS"}
- "Mostrame mis últimos 10 gastos en transporte" → \
{"periodo":"todo","metrica":"listado","categorias":["transporte"],"top_n":10,"moneda":"ARS"}
- "Compará este mes con el anterior en comida" → \
{"periodo":"este_mes","metrica":"comparar","categorias":["comida"],"top_n":5,"moneda":"ARS","periodo_comparar":"mes_pasado"}
- "Gasté más o menos que el mes pasado?" → \
{"periodo":"este_mes","metrica":"comparar","categorias":[],"top_n":5,"moneda":"ARS","periodo_comparar":"mes_pasado"}
- "Diferencia entre esta semana y la anterior en transporte" → \
{"periodo":"esta_semana","metrica":"comparar","categorias":["transporte"],"top_n":5,"moneda":"ARS","periodo_comparar":"semana_pasada"}"""


# ---------------------------------------------------------------------------
# Period resolution — string → (from_date, to_date, label)
# ---------------------------------------------------------------------------

def resolve_periodo(periodo: str, ref_date: date | None = None) -> tuple[date, date, str]:
    """Convert a period keyword into a concrete date range."""
    today = ref_date or date.today()

    match periodo:
        case "hoy":
            return today, today, "hoy"
        case "ayer":
            d = today - timedelta(days=1)
            return d, d, "ayer"
        case "esta_semana":
            monday = today - timedelta(days=today.weekday())
            return monday, today, "esta semana"
        case "semana_pasada":
            monday = today - timedelta(days=today.weekday() + 7)
            sunday = monday + timedelta(days=6)
            return monday, sunday, "la semana pasada"
        case "este_mes":
            first = today.replace(day=1)
            return first, today, "este mes"
        case "mes_pasado":
            first_this = today.replace(day=1)
            last_prev = first_this - timedelta(days=1)
            first_prev = last_prev.replace(day=1)
            return first_prev, last_prev, f"{_mes_nombre(first_prev.month)}"
        case "este_anio":
            first = date(today.year, 1, 1)
            return first, today, "este año"
        case "anio_pasado":
            first = date(today.year - 1, 1, 1)
            last = date(today.year - 1, 12, 31)
            return first, last, str(today.year - 1)
        case "ultimos_7_dias":
            return today - timedelta(days=6), today, "los últimos 7 días"
        case "ultimos_30_dias":
            return today - timedelta(days=29), today, "los últimos 30 días"
        case "ultimos_3_meses":
            return today - timedelta(days=89), today, "los últimos 3 meses"
        case "todo":
            return date(2020, 1, 1), today, "todo el historial"
        case _:
            # Fallback: este mes
            first = today.replace(day=1)
            return first, today, "este mes"


_MESES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _mes_nombre(n: int) -> str:
    return _MESES[n] if 1 <= n <= 12 else str(n)


# ---------------------------------------------------------------------------
# Category matching — fuzzy name → ID
# ---------------------------------------------------------------------------

def match_categorias(
    nombres_raw: list[str],
    catalogo: list[dict[str, Any]],
) -> list[int]:
    """
    Match raw category names from the user against the actual catalog.
    Uses case-insensitive substring matching.
    Returns list of matched category IDs.
    """
    matched: list[int] = []
    for raw in nombres_raw:
        raw_lower = raw.lower().strip()
        if not raw_lower:
            continue
        # Exact match first
        for cat in catalogo:
            if cat["nombre"].lower() == raw_lower:
                matched.append(cat["id"])
                break
        else:
            # Substring match
            for cat in catalogo:
                if raw_lower in cat["nombre"].lower() or cat["nombre"].lower() in raw_lower:
                    matched.append(cat["id"])
                    break
    return matched


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


async def parse_query(
    message: str,
    categorias_catalogo: list[dict[str, Any]],
    ref_date: date | None = None,
) -> QueryParams:
    """
    Parse a natural-language financial query into structured QueryParams.

    Args:
        message: The user's WhatsApp message
        categorias_catalogo: [{id, nombre, ...}] from categoria_repo
        ref_date: Override today's date (for testing)

    Returns:
        QueryParams with resolved dates, category IDs, and metric
    """
    logger.info("parse_query input: %r", message[:200])

    # Build system prompt with user's actual category names
    cat_names = [c["nombre"] for c in categorias_catalogo]
    system_prompt = _PARSE_SYSTEM_PROMPT
    if cat_names:
        system_prompt += (
            f"\n\nCATEGORÍAS DISPONIBLES del usuario (usá estos nombres EXACTOS en "
            f"\"categorias\"): {', '.join(cat_names)}\n"
            f"Si el usuario dice un sinónimo (ej: 'comida' → 'Alimentacion', "
            f"'auto' → 'Transporte'), mapeá al nombre exacto de la lista."
        )

    try:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=100,
            temperature=0,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = json.loads(raw)
    except Exception as e:
        logger.error("parse_query LLM failed: %s (input=%r)", e, message[:100])
        # Fallback: resumen del mes actual
        from_d, to_d, label = resolve_periodo("este_mes", ref_date)
        return QueryParams(
            from_date=from_d, to_date=to_d, periodo_label=label,
            metrica=Metrica.RESUMEN,
        )

    # Resolve period
    periodo_raw = data.get("periodo", "este_mes")
    from_d, to_d, label = resolve_periodo(periodo_raw, ref_date)

    # Resolve metric
    metrica_raw = data.get("metrica", "resumen")
    try:
        metrica = Metrica(metrica_raw)
    except ValueError:
        metrica = Metrica.RESUMEN

    # Resolve categories
    cat_nombres = data.get("categorias", [])
    cat_ids = match_categorias(cat_nombres, categorias_catalogo) if cat_nombres else []

    top_n = data.get("top_n", 5)
    if not isinstance(top_n, int) or top_n < 1:
        top_n = 5

    moneda = data.get("moneda", "ARS")
    if moneda not in ("ARS", "USD", "EUR"):
        moneda = "ARS"

    # Resolve comparison period (only for COMPARAR)
    compare_from = None
    compare_to = None
    compare_label = ""
    if metrica == Metrica.COMPARAR:
        periodo_comparar_raw = data.get("periodo_comparar", "mes_pasado")
        compare_from, compare_to, compare_label = resolve_periodo(
            periodo_comparar_raw, ref_date,
        )

    params = QueryParams(
        from_date=from_d,
        to_date=to_d,
        periodo_label=label,
        metrica=metrica,
        categorias=cat_nombres,
        categoria_ids=cat_ids,
        top_n=top_n,
        moneda=moneda,
        compare_from_date=compare_from,
        compare_to_date=compare_to,
        compare_periodo_label=compare_label,
    )
    logger.info("parse_query result: %s", params)
    return params
