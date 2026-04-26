"""Chat endpoint — AI financial assistant with real budget/spending data."""
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.services.presupuesto_analysis import budget_vs_actual, generate_suggestions
from app.services.purchase_advisor import advise_purchase
from app.repositories.movimiento_repo import list_movimientos
from app.repositories.user_repo import get_user_by_id
from app.utils.parse_utils import parse_period

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    period: str = ""  # YYYY-MM


_SYSTEM_PROMPT = """Sos un asistente financiero personal. Respondés en español argentino, casual pero informativo.
Tenés acceso a los datos reales del usuario: presupuestos, gastos, sugerencias.

Datos del usuario para este mes:
{context}

Reglas:
- Respondé de forma breve y directa, como un mensaje de WhatsApp.
- Usá *negritas* para resaltar números y categorías importantes.
- Si el usuario pregunta si puede comprar algo, analizá el presupuesto de la categoría relevante.
- Si pregunta cómo viene, dale un resumen del estado general y las categorías que se pasan.
- Si pregunta en qué gasta más, mencioná las top categorías.
- No inventes datos que no están en el contexto.
- Usá formato de moneda argentina ($X.XXX sin decimales para montos grandes)."""


async def _build_context(db: AsyncSession, id_usuario: int, period: str) -> str:
    """Build a context string with the user's financial data."""
    try:
        analysis = await budget_vs_actual(db, id_usuario, period)
    except Exception:
        analysis = None

    try:
        suggestions = await generate_suggestions(db, id_usuario, period)
    except Exception:
        suggestions = []

    # Recent transactions
    try:
        date_from, date_to = parse_period(period)
        items, total = await list_movimientos(
            db, id_usuario, from_date=date_from, to_date=date_to,
            tipo="Gasto", limit=20, offset=0,
        )
    except Exception:
        items, total = [], 0

    parts = []

    if analysis:
        parts.append(f"Periodo: {analysis['period']}")
        parts.append(f"Presupuesto total: ${analysis['total_presupuesto']:,.0f}".replace(",", "."))
        parts.append(f"Gastado total: ${analysis['total_gastado']:,.0f} ({analysis['pct_usado_global']:.0f}%)".replace(",", "."))
        parts.append(f"Restante: ${analysis['total_restante']:,.0f}".replace(",", "."))
        parts.append(f"Dias transcurridos: {analysis['dias_transcurridos']}, restantes: {analysis['dias_restantes']}")
        parts.append("\nPresupuesto por categoría:")
        for cat in analysis["categorias"]:
            parts.append(
                f"  - {cat['categoria']}: presupuesto ${cat['presupuesto']:,.0f}, "
                f"gastado ${cat['gastado']:,.0f} ({cat['pct_usado']:.0f}%), "
                f"restante ${cat['restante']:,.0f}".replace(",", ".")
            )

    if suggestions:
        parts.append("\nAlertas/sugerencias:")
        for s in suggestions[:5]:
            parts.append(f"  - [{s['tipo']}] {s['categoria']}: {s['mensaje']}")

    if items:
        parts.append(f"\nUltimas transacciones ({total} total este mes):")
        for it in items[:10]:
            desc = it.get("descripcion") or it.get("comercio") or "Sin desc"
            cat = it.get("categoria") or "Sin cat"
            parts.append(f"  - {it.get('fecha', '')} | {desc} | ${float(it.get('monto', 0)):,.0f} | {cat}".replace(",", "."))

    return "\n".join(parts) if parts else "No hay datos de presupuesto ni gastos para este periodo."


@router.post("/ask")
async def chat_ask(
    payload: ChatRequest,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Chat with the AI financial assistant using real user data."""
    from datetime import date
    from openai import AsyncOpenAI
    from app.core.config import settings

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message es requerido")

    period = payload.period
    if not period:
        today = date.today()
        period = f"{today.year}-{today.month:02d}"

    # Check if it's a purchase question — use specialized advisor
    purchase_keywords = ["puedo comprar", "me puedo comprar", "puedo gastar", "alcanza para", "me alcanza"]
    is_purchase_q = any(kw in message.lower() for kw in purchase_keywords)

    if is_purchase_q:
        user = await get_user_by_id(db, id_usuario)
        user_name = user.get("Nombre", "") if user else ""
        reply = await advise_purchase(db, id_usuario, message, user_name)
        return {"reply": reply}

    # General chat — build context and ask GPT
    context = await _build_context(db, id_usuario, period)
    system = _SYSTEM_PROMPT.replace("{context}", context)

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            max_completion_tokens=500,
        )
        reply = response.choices[0].message.content or "No pude generar una respuesta."
    except Exception as e:
        logger.error("Chat failed: %s", e)
        reply = f"Error al procesar tu consulta: {e}"

    return {"reply": reply}
