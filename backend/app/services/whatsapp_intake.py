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


# ---------------------------------------------------------------------------
# Command detection — exact match only, no heuristics
# ---------------------------------------------------------------------------
# Commands are explicit structured messages, not natural language.
# Everything that isn't a command goes to AI classification.
#
# Supported commands:
#   WEEKLY_EXPENSES_RESUME / WEEKLY_RESUME  → WEEKLY_RESUME
#   CATEGORIZAR <id>                        → CATEGORIZACION
#   CAMBIAR <id> <categoría>                → CATEGORIZACION (recategorize)
#   PRESUPUESTO: <texto>                    → PRESUPUESTO
#   SUGERENCIA(S): <texto>                  → SUGERENCIAS
# ---------------------------------------------------------------------------

_COMMANDS: list[tuple[re.Pattern, Intent, str]] = [
    (re.compile(r"^weekly[_ ]?(expenses[_ ]?)?resume$", re.IGNORECASE), Intent.WEEKLY_RESUME, "exact"),
    (re.compile(r"^categorizar\s+(\d+)$", re.IGNORECASE), Intent.CATEGORIZACION, "movimiento_id"),
    (re.compile(r"^cambiar\s+(\d+)\s+(.+)$", re.IGNORECASE), Intent.CATEGORIZACION, "cambiar"),
    (re.compile(r"^presupuesto\s*:\s*(.+)$", re.IGNORECASE), Intent.PRESUPUESTO, "raw_presupuesto"),
    (re.compile(r"^sugerencias?\s*:\s*(.+)$", re.IGNORECASE), Intent.SUGERENCIAS, "raw_sugerencia"),
]


def detect_command(body: str, button_payload: str | None = None) -> dict[str, Any] | None:
    """
    Detect explicit commands only. Returns None for any natural language message.

    Commands are structured messages that users type intentionally (or sent via
    button payloads). Everything else — expenses, queries, greetings — is NOT
    a command and should be classified by AI.
    """
    # Button payloads take priority (from interactive WhatsApp buttons)
    if button_payload:
        text = button_payload.strip().lower()
        if text in ("weekly_expenses_resume", "weekly_resume"):
            return {"intent": Intent.WEEKLY_RESUME, "command_data": {}}

    text = body.strip()
    if not text:
        return None

    for pattern, intent, data_key in _COMMANDS:
        m = pattern.match(text)
        if m:
            command_data: dict[str, Any] = {}
            if data_key == "movimiento_id" and m.lastindex and m.lastindex >= 1:
                command_data["movimiento_id"] = int(m.group(1))
            elif data_key == "cambiar" and m.lastindex and m.lastindex >= 2:
                command_data["movimiento_id"] = int(m.group(1))
                command_data["nueva_categoria"] = m.group(2).strip()
            elif data_key in ("raw_presupuesto", "raw_sugerencia") and m.lastindex and m.lastindex >= 1:
                command_data[data_key] = m.group(1).strip()
            return {"intent": intent, "command_data": command_data}

    return None


# ---------------------------------------------------------------------------
# Intent classification via OpenAI
# ---------------------------------------------------------------------------
# Only 4 intents: DATA, QUERY, SUGERENCIAS, OTHER.
# Commands (WEEKLY_RESUME, CATEGORIZAR, etc.) are already handled by
# detect_command and never reach this function.
# Sub-types of QUERY (resumen, presupuesto, categorías, etc.) are resolved
# downstream after the switch, not here.
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM_PROMPT = """\
Clasificá el mensaje de WhatsApp en UNA de estas 4 categorías.
Respondé SOLO con JSON: {"tipo": "DATA|QUERY|SUGERENCIAS|OTHER"}

DATA — El usuario quiere REGISTRAR un gasto o ingreso.
Está contando algo que ya pasó o está pasando: compró, pagó, gastó, cobró, recibió plata.
Ejemplos:
- "Gasté 5000 en el super"
- "Almorcé 3500"
- "Pagué la luz 12000"
- "taxi 2500"
- "50k en ropa"
- "300 lucas en Nike"
- "Uber hoy 1800"
- "quiero cargar un gasto"
- "nafta 15000 con débito"
- "Cobré 800k de sueldo"
- "Me pagaron 50k"
- "Me transfirieron 100k"
- "Recibí 200 dólares"
- "Me entró el sueldo, 1 palo"
Clave: menciona un monto + contexto de gasto/ingreso = DATA.

QUERY — El usuario PREGUNTA sobre sus finanzas.
Quiere saber algo, no registrar nada.
Ejemplos:
- "Cuánto gasté este mes?"
- "Gasté plata ayer?"
- "En qué categoría gasto más?"
- "Cómo vengo este mes?"
- "Dame un resumen"
- "Cuál fue mi último gasto?"
- "Cómo viene mi presupuesto?"
- "Qué categorías tengo?"
Clave: pregunta, pide info, quiere ver datos = QUERY.

SUGERENCIAS — El usuario pide CONSEJO o evaluación de una compra futura.
Quiere saber si puede/debería comprar algo.
Ejemplos:
- "Puedo comprarme unas zapatillas de 80k?"
- "Me alcanza para salir a comer?"
- "Me conviene comprar esto?"
- "Dame sugerencias para ahorrar"
- "Es caro 50k por una remera?"
Clave: compra hipotética/futura, pide opinión = SUGERENCIAS.

OTHER — No tiene NADA que ver con finanzas.
Saludos, charla, preguntas no financieras.
Ejemplos:
- "Hola"
- "Gracias"
- "Qué onda"
- "Cómo está el clima?"

REGLA: ante la duda entre DATA y QUERY, fijate si menciona un monto concreto.
Con monto → DATA. Sin monto → QUERY."""

_VALID_AI_INTENTS = frozenset({"DATA", "QUERY", "SUGERENCIAS", "OTHER"})

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


async def classify_intent(body: str) -> Intent:
    """
    Classify message intent using OpenAI.

    Only returns DATA, QUERY, SUGERENCIAS, or OTHER.
    Falls back to OTHER on error.
    """
    import json as _json

    logger.info("classify_intent input: %r", body[:200])

    try:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": body},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=30,
            temperature=0,
        )
        raw = (response.choices[0].message.content or "").strip()

        try:
            data = _json.loads(raw)
            tipo = (data.get("tipo") or "").strip().upper()
        except _json.JSONDecodeError:
            tipo = raw.upper()

        if tipo not in _VALID_AI_INTENTS:
            logger.warning(
                "classify_intent: unexpected '%s' (raw=%r) for input=%r → defaulting to OTHER",
                tipo, raw[:100], body[:100],
            )
            return Intent.OTHER

        logger.info("classify_intent result: %s (input=%r)", tipo, body[:80])
        return Intent(tipo)

    except Exception as e:
        logger.error("classify_intent failed: %s (input=%r)", e, body[:100])
        return Intent.OTHER
