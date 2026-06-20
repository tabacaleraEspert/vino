"""
Identificación de comercios nuevos.

Decisión de producto: NO usa IA. Si no hay ReglaComercio que matchee,
el movimiento queda directo como "Otros / no categorizado" para que
el usuario lo categorice a mano (y esa categorización crea la regla
para la próxima vez).
"""
from __future__ import annotations

from typing import Any


def _sin_categoria(merchant_name: str) -> dict[str, Any]:
    return {
        "merchant_raw": merchant_name,
        "merchant_identified": merchant_name,
        "rubro": "",
        "confianza": "baja",
        "categoria_id": None,
        "categoria_nombre": "",
        "subcategoria_id": None,
        "subcategoria_nombre": "",
        "explicacion": "Sin regla — categorización manual",
        "web_search_used": False,
    }


async def identify_and_suggest_category(
    merchant_name: str,
    categories: list[dict[str, Any]],
) -> dict[str, Any]:
    return _sin_categoria(merchant_name)


async def identify_merchants_batch(
    merchant_names: list[str],
    categories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [_sin_categoria(name) for name in merchant_names]
