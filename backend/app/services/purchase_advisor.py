"""Smart purchase advisor — budget-aware buying suggestions with context and alternatives."""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.presupuesto_analysis import budget_vs_actual
from app.services.smart_suggestions import compute_category_metrics, compute_month_context

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _fmt(n: float) -> str:
    return f"${n:,.0f}".replace(",", ".")


_EXTRACT_PROMPT = """Sos un asistente financiero argentino. El usuario te pregunta si puede comprar algo o ir a algún lugar.

Extraé del mensaje:
- item: qué quiere comprar o hacer (ej: "remera Nike", "comer en Marcelo", "ir al cine")
- monto: cuánto sale (número, sin $). Si no dice → null. Slang: "60k"=60000, "300 lucas"=300000
- categoria_probable: categoría de gasto (Ropa, Entretenimiento, Alimentacion, Transporte, etc.)
- es_lugar: true si menciona un lugar/restaurante/negocio específico, false si es un producto genérico
- lugar_nombre: nombre del lugar si es_lugar=true, sino null

Respondé SOLO JSON:
{
  "item": "comer en Marcelo",
  "monto": null,
  "categoria_probable": "Entretenimiento",
  "es_lugar": true,
  "lugar_nombre": "Marcelo"
}"""


_ADVICE_PROMPT = """Sos un asesor financiero argentino por WhatsApp, piola y directo.

El usuario pregunta si puede hacer una compra. Tenés estos datos reales:

PRESUPUESTO Y GASTOS:
{budget_context}

MÉTRICAS DE LA CATEGORÍA:
{metrics_context}

PREGUNTA DEL USUARIO: "{message}"
ITEM: {item}
MONTO ESTIMADO: {monto}

Tu tarea:
1. Decile si puede o no, basándote en el presupuesto restante y el ritmo de gasto
2. Si es caro para su patrón (comparar con avg_ticket), mencionalo
3. Si no puede, sugerí una alternativa más barata o decile que espere
4. Si puede pero queda justo, advertí
5. Sé breve, 2-4 líneas máximo, estilo WhatsApp con emojis y negritas

NO uses JSON. Respondé solo texto para WhatsApp."""


async def _extract_purchase(message: str) -> dict:
    """Extract item, amount, and context from user message."""
    client = _get_client()
    response = await client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": message},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=200,
    )
    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"item": None, "monto": None, "categoria_probable": None, "es_lugar": False, "lugar_nombre": None}


async def _estimate_price(item: str, lugar: str | None = None) -> float | None:
    """Use GPT to estimate price in ARS if user didn't provide one."""
    client = _get_client()
    query = f"Cuánto sale {item}" if not lugar else f"Cuánto sale comer/ir a {lugar} en Buenos Aires, Argentina"

    try:
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": "Estimá el precio en pesos argentinos (ARS) a abril 2026. Respondé SOLO JSON: {\"precio_estimado\": 25000, \"rango_bajo\": 15000, \"rango_alto\": 40000}"},
                {"role": "user", "content": query},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=100,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        return data.get("precio_estimado")
    except Exception as e:
        logger.warning("Price estimation failed: %s", e)
        return None


def _find_category_match(
    categoria_probable: str | None,
    analysis_cats: list[dict],
) -> dict | None:
    if not categoria_probable:
        return None
    target = categoria_probable.lower().strip()
    for cat in analysis_cats:
        if cat["categoria"].lower().strip() == target:
            return cat
    for cat in analysis_cats:
        cat_name = cat["categoria"].lower().strip()
        if target in cat_name or cat_name in target:
            return cat
    return None


async def advise_purchase(
    db: AsyncSession,
    id_usuario: int,
    message: str,
    user_name: str = "",
) -> str:
    """
    Analyze a purchase question and return a WhatsApp-formatted response.

    Enhanced flow:
    1. Extract what they want + amount + context (is it a place?)
    2. If no amount, estimate price with GPT
    3. Get budget status + category metrics (avg ticket, trend)
    4. Generate smart, contextual advice with GPT
    """
    today = date.today()
    period = f"{today.year}-{today.month:02d}"

    # Step 1: Extract purchase intent
    purchase = await _extract_purchase(message)
    item = purchase.get("item")
    monto = purchase.get("monto")
    cat_name = purchase.get("categoria_probable")
    es_lugar = purchase.get("es_lugar", False)
    lugar = purchase.get("lugar_nombre")

    if not item and not monto:
        return (
            "No entendí bien qué querés comprar. "
            "Decime algo como: _Puedo comprarme unas zapatillas de 80k?_ "
            "o _Puedo ir a comer a X hoy?_"
        )

    # Step 2: Estimate price if not provided
    if not monto:
        monto = await _estimate_price(item, lugar)
        monto_estimated = True
    else:
        monto_estimated = False

    # Step 3: Get budget analysis
    try:
        analysis = await budget_vs_actual(db, id_usuario, period)
    except Exception as e:
        logger.error("Budget analysis failed: %s", e)
        return "No pude obtener tu presupuesto. Asegurate de tener presupuestos cargados."

    if not analysis["categorias"]:
        return "No tenés presupuestos cargados. Andá a la app para configurarlos."

    cat_match = _find_category_match(cat_name, analysis["categorias"])
    ctx = compute_month_context(period)

    # Step 4: Get category metrics if we have a match
    metrics_text = "No hay métricas específicas."
    if cat_match and cat_match.get("categoria_id"):
        try:
            metrics = await compute_category_metrics(
                db, id_usuario, int(cat_match["categoria_id"]), period
            )
            metrics_text = (
                f"Categoría: {metrics.categoria_nombre}\n"
                f"Ticket promedio: {_fmt(metrics.avg_ticket)}\n"
                f"Ticket más caro: {_fmt(metrics.max_ticket)}\n"
                f"Transacciones este mes: {metrics.tx_count}\n"
                f"Tendencia vs mes pasado: {f'{metrics.trend_vs_last_month:+.0f}%' if metrics.trend_vs_last_month is not None else 'sin datos'}"
            )
        except Exception:
            pass

    # Build budget context
    budget_lines = [
        f"Día del mes: {ctx.days_elapsed}/{ctx.days_in_month} ({ctx.pct_month_elapsed:.0f}% transcurrido)",
        f"Presupuesto total: {_fmt(analysis['total_presupuesto'])}",
        f"Gastado total: {_fmt(analysis['total_gastado'])} ({analysis['pct_usado_global']:.0f}%)",
        f"Restante total: {_fmt(analysis['total_restante'])}",
    ]
    if cat_match:
        budget_lines.extend([
            f"\nCategoría relevante: {cat_match['categoria']}",
            f"Presupuesto categoría: {_fmt(cat_match['presupuesto'])}",
            f"Gastado categoría: {_fmt(cat_match['gastado'])} ({cat_match['pct_usado']:.0f}%)",
            f"Restante categoría: {_fmt(cat_match['restante'])}",
        ])

    budget_context = "\n".join(budget_lines)

    monto_text = _fmt(monto) if monto else "desconocido"
    if monto_estimated and monto:
        monto_text += " (estimado)"

    # Step 5: Generate advice with GPT using all context
    try:
        client = _get_client()
        prompt = _ADVICE_PROMPT.format(
            budget_context=budget_context,
            metrics_context=metrics_text,
            message=message,
            item=item or "?",
            monto=monto_text,
        )
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message},
            ],
            max_completion_tokens=300,
        )
        reply = response.choices[0].message.content or ""
        return reply.strip()
    except Exception as e:
        logger.error("Advice generation failed: %s", e)
        # Fallback: basic response
        if monto and cat_match:
            if monto > cat_match["restante"]:
                return f"Con {_fmt(cat_match['restante'])} restante en {cat_match['categoria']}, {_fmt(monto)} te pasaría del presupuesto."
            return f"Sí, tenés margen. Te queda {_fmt(cat_match['restante'])} en {cat_match['categoria']}."
        return "No pude analizar tu consulta. Probá con más detalle."
