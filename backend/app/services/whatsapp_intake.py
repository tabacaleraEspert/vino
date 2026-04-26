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


# Regex patterns to detect DATA (expense) messages without AI
_EXPENSE_PATTERNS = [
    # Contains a number that looks like a money amount (500, 1500, 50000, 50k, 300 lucas, etc.)
    re.compile(r"\b\d{3,}\b", re.IGNORECASE),  # 3+ digit number
    re.compile(r"\b\d+k\b", re.IGNORECASE),     # "50k"
    re.compile(r"\b\d+\s*lucas?\b", re.IGNORECASE),  # "300 lucas"
    re.compile(r"\b\d+\s*palos?\b", re.IGNORECASE),  # "1 palo"
    re.compile(r"\b\d+\s*gambas?\b", re.IGNORECASE),  # "2 gambas"
]

_EXPENSE_KEYWORDS = [
    "gast", "compr", "pagué", "pague", "pagó", "almor", "cené", "cene",
    "taxi", "uber", "nafta", "super", "delivery", "efectivo", "tarjeta",
    "debito", "débito", "credito", "crédito", "transferencia",
    "cargar un gasto", "agregar un gasto", "registrar un gasto", "anotar un gasto",
]


_QUERY_INDICATORS = ["cuanto", "cuánto", "cuantos", "resumen", "en qué", "en que", "último gasto", "ultimo gasto", "cómo vengo", "como vengo"]

_SUGGESTION_PATTERNS = [
    "puedo comprar", "puedo comprarme", "me puedo comprar",
    "puedo gastar", "puedo ir ", "puedo pedir", "puedo tomarme",
    "me alcanza para", "me alcanza",
    "me da para", "me conviene", "debería comprar", "deberia comprar",
    "vale la pena", "es caro", "es barato",
    "qué opinas de comprar", "que opinas de comprar",
    "me recomendas", "me puedo dar",
    "puedo darme", "me puedo permitir",
]


def _looks_like_suggestion(text: str) -> bool:
    """Check if a message is asking for purchase advice, not registering an expense."""
    lower = text.lower().strip()
    # Explicit patterns
    if any(kw in lower for kw in _SUGGESTION_PATTERNS):
        return True
    # Generic: starts with "puedo" = asking permission = suggestion
    if lower.startswith("puedo ") or lower.startswith("me puedo "):
        return True
    # Question about affordability
    if ("?" in text) and any(w in lower for w in ["comprar", "gastar", "pedir", "ir a", "comer", "salir"]):
        return True
    return False


def _looks_like_expense(text: str) -> bool:
    """Check if a message looks like an expense registration (not a query)."""
    lower = text.lower()
    # If it looks like a query about spending, NOT data entry
    if any(q in lower for q in _QUERY_INDICATORS) and "?" in text:
        return False
    # Direct expense keywords that always mean DATA
    direct_keywords = ["cargar un gasto", "agregar un gasto", "registrar un gasto", "anotar un gasto"]
    if any(kw in lower for kw in direct_keywords):
        return True
    # Check for expense action keywords + any number → DATA
    action_keywords = ["gast", "compr", "pagué", "pague", "pagó", "almor", "cené", "cene"]
    has_action = any(kw in lower for kw in action_keywords)
    has_amount = any(p.search(text) for p in _EXPENSE_PATTERNS)
    if has_action and has_amount:
        return True
    # Slang amounts with context
    has_slang_amount = bool(re.search(r"\b\d+\s*(lucas?|palos?|gambas?|k)\b", lower))
    if has_slang_amount:
        return True
    # Transport/service keywords + amount
    service_keywords = ["taxi", "uber", "nafta", "delivery"]
    if any(kw in lower for kw in service_keywords) and has_amount:
        return True
    return False


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

    # Detect suggestion/advice questions BEFORE expense detection
    if _looks_like_suggestion(text):
        return {"intent": Intent.SUGERENCIAS, "command_data": {}}

    # Detect expense messages (DATA)
    if _looks_like_expense(text):
        return {"intent": Intent.DATA, "command_data": {}}

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

_CLASSIFY_SYSTEM_PROMPT = """Sos un asistente financiero especializado en detectar la intención del usuario.
Tu única tarea es clasificar cada mensaje que llega por WhatsApp.

No respondés contenido útil. No generás texto de conversación. No registrás gastos.
Solo devolvés un JSON con la clasificación.

DEFINICIONES:

1) DATA — Mensajes que forman parte de un registro de GASTO o INGRESO.
Incluye:
- Mensajes que describen gastos o ingresos: "gasté 5000 en el super", "almorcé 3500", "pagué la luz"
- Mensajes con montos: "300 lucas en Nike", "1500 en un alfajor", "50k en ropa", "taxi 2500"
- Mensajes sueltos que completan datos: "75 mil", "con débito", "hoy", "Uber", "efectivo"
- Mensajes parcialmente estructurados: "Fecha: hoy, Monto 5000", "Gasto en YPF"
- Cualquier mensaje que mencione comprar, gastar, pagar, cobrar, o un monto de dinero
- "quiero agregar un gasto", "quiero cargar un gasto"
REGLA CLAVE: Si el mensaje menciona un monto, un comercio, o cualquier indicio de gasto/compra → SIEMPRE DATA.

2) QUERY — Preguntas sobre situación financiera:
"¿Cuánto gasté?", "¿En qué gasté más?", "¿Me hacés un resumen?", "¿Cuál fue mi último gasto?"

3) CAT_Y_SUBCATS — Consultas sobre categorías/subcategorías del sistema:
"¿Qué categorías existen?", "¿Qué subcategorías hay en Vivienda?"

4) PRESUPUESTO — Consultas sobre presupuestos:
"¿Cómo viene mi presupuesto?", "PRESUPUESTO: cuánto me queda?"

5) SUGERENCIAS — Pide consejos o si puede comprar algo:
"¿Puedo comprarme unas zapatillas de 80k?", "Dame sugerencias para ahorrar"

6) CATEGORIZACION — Quiere categorizar un movimiento existente:
"Categorizar 123", "recategorizar el último gasto"

7) WEEKLY_RESUME — Resumen semanal: solo si el mensaje es exactamente "weekly_expenses_resume"

8) OTHER — ÚLTIMO RECURSO. Solo si no encaja en NINGUNA de las anteriores.
Saludos puros ("hola"), charla casual sin contexto financiero.

PRIORIDAD: Si hay dudas entre DATA y cualquier otra → DATA.

Respondé SIEMPRE con JSON válido:
{"tipo": "<DATA|QUERY|CAT_Y_SUBCATS|PRESUPUESTO|SUGERENCIAS|CATEGORIZACION|WEEKLY_RESUME|OTHER>"}"""

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


async def classify_intent(body: str) -> Intent:
    """Classify message intent using OpenAI. Falls back to OTHER on error."""
    import json as _json
    try:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": body},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=50,
        )
        raw = (response.choices[0].message.content or "").strip()
        # Parse JSON response
        try:
            data = _json.loads(raw)
            tipo = (data.get("tipo") or "").strip().upper()
        except _json.JSONDecodeError:
            tipo = raw.upper()
        try:
            return Intent(tipo)
        except ValueError:
            logger.warning("OpenAI returned unknown intent '%s' from raw '%s', defaulting to OTHER", tipo, raw[:100])
            return Intent.OTHER
    except Exception as e:
        logger.error("Intent classification failed: %s", e)
        return Intent.OTHER
