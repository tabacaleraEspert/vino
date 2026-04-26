"""Extract expense data from natural language WhatsApp messages."""
from __future__ import annotations

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


_EXTRACT_PROMPT = """Sos un extractor de datos de gastos personales desde mensajes de WhatsApp argentinos.

Tu tarea es LEER el mensaje y extraer los datos del gasto. Entendés slang argentino:
- "300 lucas" = 300.000
- "1 palo" = 1.000.000
- "medio palo" = 500.000
- "2 gambas" = 200
- "1 luca" = 1.000
- "50k" = 50.000
- "guita" = plata/dinero

Reglas:
- monto: número entero (sin $, sin puntos de miles, sin decimales). SIEMPRE convertir slang.
- moneda: "ARS" por defecto. "USD" si dice dólares/dolar/usd/dolares.
- comercio: nombre del lugar donde gastó. Si no dice → ""
- descripcion: resumen corto del gasto
- tipo: siempre "Gasto" salvo que diga ingreso/cobré/me pagaron
- medio_de_pago: "Efectivo" por defecto. Si dice tarjeta/débito/crédito/transferencia, extraer.
- fecha: si menciona "hoy" → hoy. "ayer" → ayer. Si no dice nada → null (se usa hoy).

Respondé SOLO JSON:
{
  "monto": 5000,
  "moneda": "ARS",
  "comercio": "Jumbo",
  "descripcion": "Compra en supermercado",
  "tipo": "Gasto",
  "medio_de_pago": "Efectivo",
  "fecha": null,
  "datos_completos": true,
  "dato_faltante": null
}

Si falta el monto (=0 o no se pudo extraer):
  datos_completos = false, dato_faltante = "monto"

Si el mensaje no tiene nada que ver con un gasto:
  datos_completos = false, dato_faltante = "no_es_gasto"
"""


async def extract_expense_from_message(message: str) -> dict[str, Any]:
    """Extract expense data from a natural language message."""
    client = _get_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": _EXTRACT_PROMPT},
                {"role": "user", "content": message},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=300,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as e:
        logger.error("Expense extraction failed: %s", e)
        return {
            "monto": 0,
            "moneda": "ARS",
            "comercio": "",
            "descripcion": "",
            "tipo": "Gasto",
            "medio_de_pago": "Efectivo",
            "fecha": None,
            "datos_completos": False,
            "dato_faltante": f"error: {e}",
        }
