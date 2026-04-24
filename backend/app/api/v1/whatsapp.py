"""WhatsApp intake endpoint — receives Twilio webhook data, resolves user and classifies intent."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_master_key
from app.db.session import get_db
from app.repositories.user_repo import get_user_by_wpp
from app.services.whatsapp_intake import Intent, classify_intent, detect_command

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
