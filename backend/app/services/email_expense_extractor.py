"""Extract expense data from bank notification emails."""
from __future__ import annotations

import json
import logging
import re
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


# Regex patterns that indicate USD in email text
_USD_PATTERNS = re.compile(
    r"US\$\s*[\d.,]+"       # US$ 2.050
    r"|U\$S\s*[\d.,]+"      # U$S 2.050
    r"|USD\s*[\d.,]+"       # USD 2050
    r"|dólares"             # "dólares"
    r"|dolares"             # "dolares"
    r"|transferencia de US"  # "transferencia de US$ ..."
    , re.IGNORECASE,
)


def _text_mentions_usd(text: str) -> bool:
    """Check if text contains USD currency indicators."""
    return bool(_USD_PATTERNS.search(text))


_EXTRACT_PROMPT = """\
Extraé los datos de un gasto desde un email de notificación bancaria argentina.
El email viene de un banco o fintech (Santander, BBVA, Macro, MercadoPago, Galicia, etc.).

Extraé estos campos:
- monto: número (sin $ ni puntos ni comas). Si hay moneda extranjera, convertí a la moneda indicada.
- moneda: "ARS" por defecto. "USD" si dice dólares, US$, USD, U$S, o cualquier referencia a dólares/moneda extranjera.
- comercio_raw: nombre del comercio tal como aparece en el email.
- descripcion: resumen corto (ej: "Compra en Carrefour", "Transferencia a Juan").
- tipo: "Gasto" para compras/pagos/transferencias enviadas. "Ingreso" para cobros/transferencias recibidas.
- medio_de_pago: extraer si dice crédito/débito/transferencia + banco/tarjeta. Ej: "Visa Crédito Santander".
- fecha: en formato YYYY-MM-DD si aparece en el email. Si no → null.
- datos_completos: true si pudiste extraer al menos monto y comercio/descripcion. false si el email no es un gasto.

Si el email NO es una notificación de gasto (ej: resumen mensual, promo, newsletter):
- datos_completos: false
- dato_faltante: "no_es_gasto"

Respondé SOLO JSON válido:
{"monto": N, "moneda": "ARS", "comercio_raw": "", "descripcion": "", "tipo": "Gasto", \
"medio_de_pago": "", "fecha": null, "datos_completos": true}"""


async def extract_expense_from_email(
    subject: str,
    sender: str,
    body: str,
) -> dict[str, Any]:
    """
    Extract expense data from a bank notification email using GPT.

    Args:
        subject: Email subject line
        sender: Sender email address
        body: Plain text body (HTML already stripped)

    Returns:
        Dict with extracted fields, or datos_completos=False if not an expense.
    """
    # Truncate body to avoid token waste — bank notifications are short
    body_truncated = body[:2000] if body else ""

    user_message = (
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"---\n"
        f"{body_truncated}"
    )

    logger.info("email_extract input: subject=%r sender=%r body_len=%d", subject, sender, len(body))

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": _EXTRACT_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=200,
            temperature=0,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = json.loads(raw)

        # Post-extraction USD detection — GPT sometimes misses "US$" / "U$S"
        if data.get("moneda", "ARS") == "ARS" and data.get("datos_completos"):
            full_text = f"{subject} {body_truncated}"
            if _text_mentions_usd(full_text):
                logger.info("email_extract: overriding moneda ARS→USD based on text indicators")
                data["moneda"] = "USD"

        logger.info("email_extract result: %s", {k: v for k, v in data.items() if k != "body"})
        return data
    except Exception as e:
        logger.error("email_extract failed: %s", e)
        return {"datos_completos": False, "dato_faltante": "extraction_error"}
