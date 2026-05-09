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

Reglas:
- monto: número entero, SIEMPRE convertir slang. Sin $ ni puntos.
- moneda: detectar la moneda según lo que dice el usuario:
  - "ARS" por defecto si no menciona moneda explícitamente.
  - "USD" SOLO si el usuario dice explícitamente "dólares", "dólar", "dolares", "dolar", "USD", "usd", "us$", "U$S".
  - NO inferir la moneda por el monto. Un gasto de $50 sin mención de moneda es ARS.
  - Si el mensaje es ambiguo y no menciona moneda → usar "ARS".
- comercio: nombre del lugar. Si no dice nombre de local → ""
- descripcion: resumen corto y claro del gasto (ej: "Alfajor en kiosco", "Almuerzo", "Nafta YPF")
- tipo: "Gasto" siempre, salvo que diga ingreso/cobré/me pagaron
- medio_de_pago: "Efectivo" por defecto. Si dice tarjeta/débito/crédito/transferencia, extraer.
- fecha: "hoy" → hoy, "ayer" → ayer, si no dice → null
- categoria_sugerida: basándote en el gasto, sugerí la categoría más probable de esta lista:
{categories_text}
  Si no estás seguro → null

CUOTAS: Si el usuario menciona cuotas, extraer:
- cuota_actual: número de cuota actual (ej: "cuota 3 de 6" → 3)
- cuota_total: total de cuotas (ej: "cuota 3 de 6" → 6)
- monto_total_compra: monto total de la compra si se menciona
  Si dice "en 6 cuotas de 5000" → monto = 5000, cuota_total = 6, monto_total_compra = 30000
  Si dice "compré algo de 300k en 12 cuotas" → monto = 25000, cuota_total = 12, monto_total_compra = 300000

PAGUÉ YO (split): Si el usuario dice "pagué yo", "dividimos", "somos X", extraer:
- es_split: true
- split_participantes: cantidad de personas (incluido el usuario)
- split_nombres: lista de nombres si los menciona
  Si dice "pagué yo la cena, somos 4" → es_split = true, split_participantes = 4
  El monto registrado es el TOTAL (lo que pagó), no la parte de cada uno

Respondé SOLO JSON:
{{
  "monto": 1500,
  "moneda": "ARS",
  "comercio": "",
  "descripcion": "Alfajor",
  "tipo": "Gasto",
  "medio_de_pago": "Efectivo",
  "fecha": null,
  "categoria_sugerida": "Alimentacion",
  "subcategoria_sugerida": "Kiosco",
  "cuota_actual": null,
  "cuota_total": null,
  "monto_total_compra": null,
  "es_split": false,
  "split_participantes": null,
  "split_nombres": [],
  "datos_completos": true,
  "dato_faltante": null
}}

Si falta el monto → datos_completos = false, dato_faltante = "monto"
Si no es un gasto → datos_completos = false, dato_faltante = "no_es_gasto"
"""


async def extract_expense_from_message(
    message: str,
    categories: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Extract expense data from a natural language message."""
    client = _get_client()

    # Build categories text for the prompt
    cats_text = ""
    if categories:
        lines = []
        for c in categories:
            subs = c.get("subcategorias", [])
            sub_names = ", ".join(s.get("nombre", "") for s in subs) if subs else ""
            line = f"  - {c.get('nombre', '')} (id={c.get('id', '')})"
            if sub_names:
                line += f": {sub_names}"
            lines.append(line)
        cats_text = "\n".join(lines)
    else:
        cats_text = "  (no disponibles)"

    prompt = _EXTRACT_PROMPT.replace("{categories_text}", cats_text)

    try:
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": prompt},
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
