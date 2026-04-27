"""Read a photo of a receipt/ticket and extract expense data using Vision API."""
from __future__ import annotations

import base64
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _build_categories_json(categories: list[dict[str, Any]]) -> str:
    cats = []
    for c in categories:
        entry: dict[str, Any] = {"id": c.get("id"), "nombre": c.get("nombre", "")}
        subs = c.get("subcategorias", [])
        if subs:
            entry["subcategorias"] = [
                {"id": s.get("id"), "nombre": s.get("nombre", "")} for s in subs
            ]
        cats.append(entry)
    return json.dumps(cats, ensure_ascii=False)


_TICKET_PROMPT = """Sos un extractor de datos de tickets/recibos/facturas argentinos.

Analizá la foto del ticket y extraé:
- monto_total: el total a pagar (número, sin $, sin puntos de miles)
- comercio: nombre del local/comercio que aparece en el ticket
- fecha: fecha del ticket en formato YYYY-MM-DD (si se ve)
- items: lista de items con nombre y precio (máximo 10)
- moneda: "ARS" por defecto, "USD" si aparece
- medio_de_pago: si se ve (efectivo, tarjeta, etc.)
- descripcion: resumen corto del gasto

Entendé formato argentino:
- Puntos son separadores de miles: 1.500 = mil quinientos
- Coma es decimal: 1.500,50 = mil quinientos con 50 centavos

Categorías disponibles del usuario:
{categories_json}

Sugerí la categoría más apropiada:
- categoria_sugerida: nombre de la categoría
- subcategoria_sugerida: nombre de la subcategoría

Respondé SOLO JSON:
{{
  "monto_total": 15000,
  "comercio": "McDonald's",
  "fecha": "2026-04-27",
  "moneda": "ARS",
  "medio_de_pago": "Efectivo",
  "descripcion": "Almuerzo en McDonald's",
  "categoria_sugerida": "Alimentos",
  "subcategoria_sugerida": "Restaurant",
  "items": [
    {{"nombre": "Big Mac", "precio": 8500}},
    {{"nombre": "Coca Cola", "precio": 3500}}
  ],
  "datos_completos": true
}}

Si no podés leer el ticket, devolvé datos_completos: false."""


async def read_ticket_photo(
    image_bytes: bytes,
    mime_type: str,
    categories: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract expense data from a receipt/ticket photo."""
    client = _get_client()
    cats_json = _build_categories_json(categories)
    prompt = _TICKET_PROMPT.replace("{categories_json}", cats_json)
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Leé este ticket y extraé los datos del gasto:"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "high"},
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=1000,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as e:
        logger.error("Ticket reading failed: %s", e)
        return {"datos_completos": False, "error": str(e)}
