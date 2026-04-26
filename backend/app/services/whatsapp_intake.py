"""Service for WhatsApp message intake: command detection and intent classification."""
from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    DATA = "DATA"
    QUERY = "QUERY"
    CAT_Y_SUBCATS = "CAT_Y_SUBCATS"
    PRESUPUESTO = "PRESUPUESTO"
    SUGERENCIAS = "SUGERENCIAS"
    CATEGORIZACION = "CATEGORIZACION"
    WEEKLY_RESUME = "WEEKLY_RESUME"
    OTHER = "OTHER"


# --- Command detection (regex, no AI needed) ---

_COMMANDS: list[tuple[re.Pattern, Intent, str]] = [
    # Exact match for weekly resume (case-insensitive)
    (re.compile(r"^weekly_expenses_resume$", re.IGNORECASE), Intent.WEEKLY_RESUME, "exact"),
    # CATEGORIZAR followed by a number
    (re.compile(r"^categorizar\s+(\d+)", re.IGNORECASE), Intent.CATEGORIZACION, "movimiento_id"),
    # PRESUPUESTO: followed by content
    (re.compile(r"^presupuesto\s*:\s*(.+)", re.IGNORECASE), Intent.PRESUPUESTO, "raw_presupuesto"),
    # SUGERENCIA(S): followed by content
    (re.compile(r"^sugerencias?\s*:\s*(.+)", re.IGNORECASE), Intent.SUGERENCIAS, "raw_sugerencia"),
]


def detect_command(body: str, button_payload: str | None = None) -> dict[str, Any] | None:
    """Detect commands via regex or button payload. Returns None if no match."""
    # Check button payload first (e.g., from interactive WhatsApp buttons)
    if button_payload:
        text = button_payload.strip()
        if text.lower() == "weekly_expenses_resume":
            return {"intent": Intent.WEEKLY_RESUME, "command_data": {}}

    text = body.strip()
    if not text:
        return None

    for pattern, intent, data_key in _COMMANDS:
        m = pattern.match(text)
        if m:
            command_data = {}
            if data_key == "movimiento_id" and m.lastindex and m.lastindex >= 1:
                command_data["movimiento_id"] = int(m.group(1))
            elif data_key in ("raw_presupuesto", "raw_sugerencia") and m.lastindex and m.lastindex >= 1:
                command_data[data_key] = m.group(1).strip()
            return {"intent": intent, "command_data": command_data}

    return None


# --- Intent classification via OpenAI ---

_CLASSIFY_SYSTEM_PROMPT = """Sos un clasificador de intención para un asistente financiero por WhatsApp.
Tu única tarea es clasificar el mensaje del usuario en UNA de estas categorías:

- DATA: el usuario está registrando un gasto/ingreso o completando datos de uno (monto, fecha, comercio, etc.)
- QUERY: pregunta sobre su situación financiera (cuánto gastó, resumen, análisis)
- CAT_Y_SUBCATS: consulta sobre categorías o subcategorías disponibles
- PRESUPUESTO: consulta o acción relacionada con presupuestos
- SUGERENCIAS: pide sugerencias o consejos financieros
- CATEGORIZACION: quiere categorizar o recategorizar un movimiento
- WEEKLY_RESUME: pide un resumen semanal de gastos
- OTHER: no encaja en ninguna categoría anterior

Si hay duda entre DATA y QUERY, priorizá DATA si parece que el usuario está cargando un gasto.

Respondé SOLO con la categoría, sin explicación. Ejemplo: DATA"""

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


async def classify_intent(body: str) -> Intent:
    """Classify message intent using OpenAI. Falls back to OTHER on error."""
    try:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": body},
            ],
            max_completion_tokens=20,
        )
        raw = (response.choices[0].message.content or "").strip().upper()
        try:
            return Intent(raw)
        except ValueError:
            logger.warning("OpenAI returned unknown intent '%s', defaulting to OTHER", raw)
            return Intent.OTHER
    except Exception as e:
        logger.error("Intent classification failed: %s", e)
        return Intent.OTHER
