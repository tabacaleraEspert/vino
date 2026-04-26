"""Service for purchase advice based on budget status."""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.presupuesto_analysis import budget_vs_actual

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


_EXTRACT_PROMPT = """Extraé del mensaje del usuario qué quiere comprar y por cuánto.
Devolvé JSON:
{
  "item": "remera Nike",
  "monto": 60000,
  "categoria_probable": "Ropa"
}
Si no hay monto claro, poné null. Si no podés extraer nada, devolvé {"item": null, "monto": null, "categoria_probable": null}."""


async def _extract_purchase(message: str) -> dict:
    """Extract item, amount, and probable category from user message."""
    client = _get_client()
    response = await client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": message},
        ],
        response_format={"type": "json_object"},
        max_tokens=100,
        temperature=0,
    )
    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"item": None, "monto": None, "categoria_probable": None}


def _find_category_match(
    categoria_probable: str | None,
    analysis_cats: list[dict],
) -> dict | None:
    """Find the best matching category from budget analysis."""
    if not categoria_probable:
        return None
    target = categoria_probable.lower().strip()
    for cat in analysis_cats:
        if cat["categoria"].lower().strip() == target:
            return cat
    # Fuzzy: check if target is contained in category name or vice versa
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

    Flow:
    1. Extract what they want to buy + amount from the message
    2. Get current month's budget vs actual
    3. Find the matching category
    4. Generate advice based on budget status
    """
    today = date.today()
    period = f"{today.year}-{today.month:02d}"

    # Step 1: Extract purchase intent
    purchase = await _extract_purchase(message)
    item = purchase.get("item")
    monto = purchase.get("monto")
    cat_name = purchase.get("categoria_probable")

    if not item and not monto:
        return (
            "No entendi bien que queres comprar. "
            "Decime algo como: _Puedo comprarme unas zapatillas de 80k?_"
        )

    # Step 2: Get budget analysis
    try:
        analysis = await budget_vs_actual(db, id_usuario, period)
    except Exception as e:
        logger.error("Budget analysis failed: %s", e)
        return "No pude obtener tu presupuesto. Asegurate de tener presupuestos cargados para este mes."

    if not analysis["categorias"]:
        return (
            "No tenes presupuestos cargados para este mes. "
            "Anda a la seccion de Presupuestos en la app para configurarlos."
        )

    # Step 3: Find matching category
    cat_match = _find_category_match(cat_name, analysis["categorias"])

    # Step 4: Build response
    dias_restantes = analysis["dias_restantes"]
    greeting = f"*{user_name}*" if user_name else "Che"

    if monto and cat_match:
        presup = cat_match["presupuesto"]
        gastado = cat_match["gastado"]
        restante = cat_match["restante"]
        pct = cat_match["pct_usado"]
        cat_display = cat_match["categoria"]

        item_display = f"*{item}*" if item else "eso"
        monto_display = f"${monto:,.0f}".replace(",", ".")

        if presup <= 0:
            # No budget for this category
            return (
                f"{greeting}, no tenes presupuesto definido para *{cat_display}*. "
                f"Este mes ya gastaste ${gastado:,.0f} ahi.\n\n".replace(",", ".") +
                f"Si queres comprar {item_display} por {monto_display}, "
                "te recomiendo primero definir un presupuesto para esa categoria."
            )

        if pct > 100:
            # Already over budget
            exceso = gastado - presup
            return (
                f"Uh {greeting}, ya estas *pasado* en *{cat_display}*.\n\n"
                f"Presupuesto: ${presup:,.0f}\n".replace(",", ".") +
                f"Gastado: ${gastado:,.0f} ({pct:.0f}%)\n".replace(",", ".") +
                f"Excedido por: ${exceso:,.0f}\n\n".replace(",", ".") +
                f"Comprar {item_display} por {monto_display} te pasaria aun mas. "
                "Yo esperaria al mes que viene."
            )

        if monto > restante:
            # Would go over budget
            return (
                f"{greeting}, en *{cat_display}* te queda "
                f"${restante:,.0f} de ${presup:,.0f}".replace(",", ".") +
                f" ({pct:.0f}% usado).\n\n"
                f"Comprar {item_display} por {monto_display} te pasaria del presupuesto "
                f"por ${(monto - restante):,.0f}.\n\n".replace(",", ".") +
                (f"Faltan {dias_restantes} dias para fin de mes. "
                 "Yo lo pensaria." if dias_restantes > 3 else
                 "Ya casi termina el mes, bankatelo.")
            )

        # Can afford it
        new_remaining = restante - monto
        new_pct = ((gastado + monto) / presup * 100) if presup > 0 else 0
        return (
            f"Si {greeting}, podes! En *{cat_display}* te queda "
            f"${restante:,.0f} de ${presup:,.0f}".replace(",", ".") +
            f" ({pct:.0f}% usado).\n\n"
            f"Si compras {item_display} por {monto_display}, "
            f"te quedarian ${new_remaining:,.0f} ".replace(",", ".") +
            f"({new_pct:.0f}% usado).\n\n" +
            (f"Faltan {dias_restantes} dias, estas bien. Dale tranqui."
             if new_pct < 80 else
             f"Ojo que quedas en {new_pct:.0f}%, ajusta el resto del mes.")
        )

    elif monto and not cat_match:
        # Has amount but couldn't match category
        total_restante = analysis["total_restante"]
        total_pct = analysis["pct_usado_global"]
        item_display = f"*{item}*" if item else "eso"
        monto_display = f"${monto:,.0f}".replace(",", ".")

        if total_pct > 100:
            return (
                f"{greeting}, en general ya estas *pasado* del presupuesto total "
                f"({total_pct:.0f}% usado).\n\n"
                f"Comprar {item_display} por {monto_display} no es buena idea ahora."
            )

        if monto > total_restante:
            return (
                f"{greeting}, en total te queda ${total_restante:,.0f} ".replace(",", ".") +
                f"de presupuesto ({total_pct:.0f}% usado).\n\n"
                f"Comprar {item_display} por {monto_display} te pasaria del presupuesto total."
            )

        return (
            f"No encontre la categoria exacta, pero en general te queda "
            f"${total_restante:,.0f} de presupuesto ".replace(",", ".") +
            f"({total_pct:.0f}% usado).\n\n"
            f"Comprar {item_display} por {monto_display} entra. "
            f"Faltan {dias_restantes} dias para fin de mes."
        )

    else:
        # No amount
        return (
            f"Decime cuanto sale y te digo si entra en tu presupuesto. "
            f"Ej: _Puedo comprarme {item or 'unas zapas'} de 50k?_"
        )
