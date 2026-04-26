"""WhatsApp endpoints — intake, purchase advice, and more."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_master_key
from app.db.session import get_db
from app.repositories.user_repo import get_user_by_wpp
from app.services.whatsapp_intake import Intent, classify_intent, detect_command
from app.services.purchase_advisor import advise_purchase

logger = logging.getLogger(__name__)
router = APIRouter()


class IntakeRequest(BaseModel):
    From: str  # "whatsapp:+5491112345678"
    Body: str = ""
    WaId: str = ""
    ButtonPayload: str | None = None


@router.post("/intake")
async def whatsapp_intake(
    payload: IntakeRequest,
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Intake de mensajes WhatsApp desde n8n/Twilio.

    1. Resuelve usuario por WppEntero
    2. Detecta comandos por regex (sin IA)
    3. Si no es comando, clasifica intención con OpenAI
    4. Devuelve intent + user para que n8n rutee
    """
    # --- 1. Resolver usuario ---
    wpp_from = payload.From.strip()
    user = await get_user_by_wpp(db, wpp_from)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuario con WppEntero '{wpp_from}' no encontrado")

    user_summary = {
        "id": user["id"],
        "nombre": user.get("Nombre", ""),
        "wpp_entero": user.get("WppEntero", ""),
    }

    body = payload.Body.strip()

    # --- 2. Detectar comando por regex ---
    cmd = detect_command(body, payload.ButtonPayload)
    if cmd:
        return {
            "intent": cmd["intent"].value,
            "command_match": True,
            "command_data": cmd["command_data"],
            "user": user_summary,
            "raw_body": body,
        }

    # --- 3. Clasificar intención con IA ---
    intent = await classify_intent(body)

    return {
        "intent": intent.value,
        "command_match": False,
        "command_data": {},
        "user": user_summary,
        "raw_body": body,
    }


# ---------------------------------------------------------------------------
# Purchase advice
# ---------------------------------------------------------------------------

class PurchaseAdviceRequest(BaseModel):
    user_id: int
    message: str
    user_name: str = ""


@router.post("/suggest-purchase")
async def suggest_purchase(
    payload: PurchaseAdviceRequest,
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Responde si el usuario puede comprar algo según su presupuesto.

    Ejemplo: "Puedo comprarme una remera de 60k?"
    → Analiza el presupuesto de la categoría, calcula si entra, devuelve
      un mensaje listo para enviar por WhatsApp.
    """
    reply = await advise_purchase(
        db,
        id_usuario=payload.user_id,
        message=payload.message,
        user_name=payload.user_name,
    )
    return {"reply": reply}
