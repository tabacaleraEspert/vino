"""Repositorio para resolución de medios de pago."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medio_pago import CardFundingType, PaymentMethodCatalog


def _norm(s: str) -> str:
    if not s:
        return ""
    t = unicodedata.normalize("NFD", s)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.lower().strip()


# Mapeo from → entidad para fallback
_FROM_TO_ENTIDAD = {
    "santander": "santander",
    "bbva": "bbva",
    "macro": "macro",
    "galicia": "galicia",
    "mercadopago": "mercado pago",
    "mercadolibre": "mercado pago",
}


async def resolve_medio_pago(
    session: AsyncSession,
    medio_pago_raw: str,
    from_email: str = "",
    asunto: str = "",
) -> dict[str, Any]:
    """
    Resuelve medio de pago a partir de texto libre.
    Retorna dict con id_credito_debito, id_medio_pago_final, etc.
    Si no matchea, retorna dict con valores None.
    """
    # Cargar catálogo con LEFT JOIN (medios sin crédito/débito incluidos)
    stmt = (
        select(
            CardFundingType.name.label("credito_debito"),
            CardFundingType.card_funding_type_id.label("id_credito_debito"),
            PaymentMethodCatalog.medio_de_pago_final,
            PaymentMethodCatalog.id_medio_de_pago_final,
        )
        .select_from(PaymentMethodCatalog)
        .outerjoin(
            CardFundingType,
            CardFundingType.card_funding_type_id == PaymentMethodCatalog.card_funding_type_id,
        )
        .where(PaymentMethodCatalog.is_active == True)  # noqa: E712
    )
    result = await session.execute(stmt)
    catalogo = [dict(row._mapping) for row in result.all()]

    if not catalogo:
        return _empty_result()

    texto = f"{_norm(medio_pago_raw)} {_norm(from_email)} {_norm(asunto)}"

    # 1. Detectar crédito vs débito
    id_credito_debito = None
    credito_debito = ""
    if re.search(r"credito|credit", texto):
        for c in catalogo:
            if c["credito_debito"] and _norm(c["credito_debito"]) == "credito":
                id_credito_debito = c["id_credito_debito"]
                credito_debito = "Credito"
                break
    elif re.search(r"debito|debit", texto):
        for c in catalogo:
            if c["credito_debito"] and _norm(c["credito_debito"]) == "debito":
                id_credito_debito = c["id_credito_debito"]
                credito_debito = "Debito"
                break

    # 2. Matchear medio de pago por nombre (buscar el más largo que matchee)
    id_medio_pago_final = None
    medio_de_pago_final = ""
    best_len = 0
    for c in catalogo:
        medio = c["medio_de_pago_final"]
        medio_norm = _norm(medio)
        if not medio_norm:
            continue
        # Buscar tokens del medio en el texto (no substring exacto)
        tokens = medio_norm.replace("-", " ").split()
        if all(t in texto for t in tokens) and len(medio_norm) > best_len:
            if id_credito_debito is None or c["id_credito_debito"] is None or c["id_credito_debito"] == id_credito_debito:
                id_medio_pago_final = c["id_medio_de_pago_final"]
                medio_de_pago_final = medio
                best_len = len(medio_norm)
                if id_credito_debito is None and c["id_credito_debito"]:
                    id_credito_debito = c["id_credito_debito"]
                    credito_debito = c["credito_debito"] or ""

    # 3. Fallback: intentar por from del email
    if not id_medio_pago_final:
        from_norm = _norm(from_email)
        for key, search in _FROM_TO_ENTIDAD.items():
            if key in from_norm:
                for c in catalogo:
                    if search in _norm(c["medio_de_pago_final"]):
                        if id_credito_debito is None or c["id_credito_debito"] is None or c["id_credito_debito"] == id_credito_debito:
                            id_medio_pago_final = c["id_medio_de_pago_final"]
                            medio_de_pago_final = c["medio_de_pago_final"]
                            if id_credito_debito is None and c["id_credito_debito"]:
                                id_credito_debito = c["id_credito_debito"]
                                credito_debito = c["credito_debito"] or ""
                            break
                break

    return {
        "id_credito_debito": id_credito_debito,
        "id_medio_pago_final": id_medio_pago_final,
        "credito_debito": credito_debito,
        "medio_de_pago_final": medio_de_pago_final,
    }


def _empty_result() -> dict[str, Any]:
    return {
        "id_credito_debito": None,
        "id_medio_pago_final": None,
        "credito_debito": "",
        "medio_de_pago_final": "",
    }
