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
from app.services.expense_extractor import extract_expense_from_message

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


# ---------------------------------------------------------------------------
# Query — answer financial questions via WhatsApp
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    user_id: int
    message: str
    user_name: str = ""


@router.post("/query")
async def whatsapp_query(
    payload: QueryRequest,
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Answer financial questions from WhatsApp.
    Reuses the chat logic but with master key auth (for n8n).

    Handles: "cuánto gasté este mes?", "en qué categoría gasto más?",
    "cómo viene mi presupuesto?", etc.
    """
    from datetime import date
    from app.api.v1.chat import _build_context, _SYSTEM_PROMPT
    from openai import AsyncOpenAI
    from app.core.config import settings

    message = payload.message.strip()
    if not message:
        return {"reply": "No recibí ninguna pregunta."}

    today = date.today()
    period = f"{today.year}-{today.month:02d}"

    context = await _build_context(db, payload.user_id, period)
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
        logger.error("WhatsApp query failed: %s", e)
        reply = f"Error: {e}"

    return {"reply": reply}


# ---------------------------------------------------------------------------
# Register expense from WhatsApp message
# ---------------------------------------------------------------------------

class RegisterExpenseRequest(BaseModel):
    user_id: int
    message: str
    user_name: str = ""


@router.post("/register-expense")
async def register_expense(
    payload: RegisterExpenseRequest,
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Register an expense from a natural language WhatsApp message.

    Flow:
    1. GPT extracts: monto, comercio, descripcion, moneda, tipo, medio_de_pago
    2. Resolve merchant rule for category
    3. If no rule: AI identifies merchant + suggests category
    4. Resolve payment method
    5. Create movement
    6. Return WhatsApp-ready confirmation message

    Handles Argentine slang: "300 lucas", "1 palo", "50k", etc.
    """
    from datetime import date, timedelta
    from decimal import Decimal

    from app.repositories.categoria_repo import list_categorias, list_subcategorias
    from app.repositories.movimiento_repo import create_movimiento
    from app.repositories.regla_repo import resolve_regla, create_regla
    from app.repositories.medio_pago_repo import resolve_medio_pago
    from app.services.merchant_identifier import identify_merchant

    message = payload.message.strip()
    if not message:
        return {"status": "error", "reply": "No recibí ningún mensaje."}

    # Load categories for the extractor
    cats = await list_categorias(db, payload.user_id)
    subs = await list_subcategorias(db, payload.user_id)
    sub_by_cat: dict[int, list] = {}
    for s in subs:
        cid = s.get("categoria_id")
        if cid:
            sub_by_cat.setdefault(cid, []).append(s)
    cats_with_subs = [{**c, "subcategorias": sub_by_cat.get(c["id"], [])} for c in cats]

    # Step 1: Extract expense data from message (with categories context)
    extracted = await extract_expense_from_message(message, cats_with_subs)

    if not extracted.get("datos_completos"):
        faltante = extracted.get("dato_faltante", "")
        if faltante == "no_es_gasto":
            return {
                "status": "not_expense",
                "reply": "No parece ser un gasto. Si querés registrar algo, decime algo como: _Gasté 5000 en el super_",
            }
        if faltante == "monto":
            return {
                "status": "incomplete",
                "reply": "No pude detectar el monto. Decime cuánto gastaste, ej: _Gasté 5000 en Carrefour_",
                "extracted": extracted,
            }
        return {
            "status": "incomplete",
            "reply": f"Me falta info: {faltante}. Probá de vuelta con más detalle.",
            "extracted": extracted,
        }

    monto = extracted.get("monto", 0)
    if not monto or monto <= 0:
        return {
            "status": "incomplete",
            "reply": "El monto tiene que ser mayor a 0. Decime cuánto gastaste.",
        }

    moneda = extracted.get("moneda", "ARS") or "ARS"
    comercio_raw = extracted.get("comercio", "") or ""
    descripcion = extracted.get("descripcion", "") or comercio_raw or "Gasto WhatsApp"
    tipo = extracted.get("tipo", "Gasto") or "Gasto"
    medio_pago_raw = extracted.get("medio_de_pago", "") or ""

    # Parse fecha
    fecha_str = extracted.get("fecha")
    today = date.today()
    if fecha_str == "ayer":
        fecha = today - timedelta(days=1)
    elif fecha_str and fecha_str != "null":
        from app.utils.parse_utils import parse_date_flex
        fecha = parse_date_flex(fecha_str) or today
    else:
        fecha = today

    # Step 2: Resolve category via merchant rules
    id_categoria = None
    id_subcategoria = None
    regla_match = None
    categoria_nombre = ""
    subcategoria_nombre = ""

    if comercio_raw:
        regla_match = await resolve_regla(db, payload.user_id, comercio_raw)
        if regla_match:
            id_categoria = regla_match["categoria_id"]
            id_subcategoria = regla_match["subcategoria_id"]
            categoria_nombre = regla_match.get("categoria_nombre", "")
            subcategoria_nombre = regla_match.get("subcategoria_nombre", "")

    # Step 3: If no rule match, try AI merchant identification
    if not id_categoria and comercio_raw:
        try:
            ai_result = await identify_merchant(comercio_raw, cats_with_subs, use_web_search=False)
            if ai_result.get("confianza") in ("alta", "media") and ai_result.get("categoria_id"):
                id_categoria = ai_result["categoria_id"]
                id_subcategoria = ai_result.get("subcategoria_id")
                try:
                    await create_regla(
                        db, id_usuario=payload.user_id, patron=comercio_raw,
                        id_categoria=id_categoria, id_subcategoria=id_subcategoria,
                        confianza=f"AI_{ai_result['confianza']}",
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.warning("AI merchant identification failed: %s", e)

    # Step 3b: Use GPT's category suggestion from the extraction
    if not id_categoria:
        cat_sug = extracted.get("categoria_sugerida", "")
        sub_sug = extracted.get("subcategoria_sugerida", "")
        if cat_sug:
            for c in cats:
                if c.get("nombre", "").lower() == str(cat_sug).lower():
                    id_categoria = c["id"]
                    categoria_nombre = c.get("nombre", "")
                    for s in sub_by_cat.get(c["id"], []):
                        if sub_sug and s.get("nombre", "").lower() == str(sub_sug).lower():
                            id_subcategoria = s["id"]
                            subcategoria_nombre = s.get("nombre", "")
                            break
                    break

    # Default if nothing matched
    if not id_categoria:
        id_categoria = 6
        id_subcategoria = 42
        categoria_nombre = "Otros"
        subcategoria_nombre = "Gastos no categorizados"

    # Resolve names if we have IDs but no names yet
    if id_categoria and not categoria_nombre:
        for c in cats:
            if c["id"] == id_categoria:
                categoria_nombre = c.get("nombre", "")
                for s in sub_by_cat.get(c["id"], []):
                    if s["id"] == id_subcategoria:
                        subcategoria_nombre = s.get("nombre", "")
                break

    # Step 4: Resolve payment method
    id_credito_debito = None
    id_medio_pago_final = None
    if medio_pago_raw and medio_pago_raw.lower() != "efectivo":
        try:
            medio = await resolve_medio_pago(db, medio_pago_raw, "", "")
            id_credito_debito = medio.get("id_credito_debito")
            id_medio_pago_final = medio.get("id_medio_pago_final")
        except Exception:
            pass

    # Step 5: Create movement
    try:
        created = await create_movimiento(
            db,
            id_usuario=payload.user_id,
            fecha=fecha,
            tipo=tipo,
            moneda=moneda,
            monto=Decimal(str(monto)),
            medio_carga="Wpp",
            descripcion=descripcion,
            id_categoria=id_categoria,
            id_subcategoria=id_subcategoria,
            comercio_id=str(regla_match["id"]) if regla_match else None,
            categoria_manual=False,
            origen="Wpp",
            origen_id=None,
            id_credito_debito=id_credito_debito,
            id_medio_pago_final=id_medio_pago_final,
        )
    except Exception as e:
        logger.error("Failed to create movement: %s", e)
        return {"status": "error", "reply": f"Error al registrar el gasto: {e}"}

    # Step 6: Build WhatsApp confirmation (conversational style)
    monto_fmt = f"${monto:,.0f}".replace(",", ".")
    emoji = "💸"
    if categoria_nombre.lower() in ("alimentacion", "alimentos"):
        emoji = "🍽️"
    elif categoria_nombre.lower() in ("transporte",):
        emoji = "🚗"
    elif categoria_nombre.lower() in ("entretenimiento",):
        emoji = "🎬"
    elif categoria_nombre.lower() in ("salud",):
        emoji = "💊"
    elif categoria_nombre.lower() in ("ropa",):
        emoji = "👕"
    elif categoria_nombre.lower() in ("vivienda", "servicios"):
        emoji = "🏠"
    elif categoria_nombre.lower() in ("educacion", "educación"):
        emoji = "📚"

    reply = f"{emoji} *{monto_fmt}*"
    if moneda != "ARS":
        reply += f" {moneda}"
    if comercio_raw:
        reply += f" en *{comercio_raw}*"
    elif descripcion and descripcion != "Gasto WhatsApp":
        reply += f" — {descripcion}"

    reply += f"\n📂 {categoria_nombre}"
    if subcategoria_nombre and subcategoria_nombre != "Gastos no categorizados":
        reply += f" / {subcategoria_nombre}"

    if medio_pago_raw and medio_pago_raw.lower() != "efectivo":
        reply += f"\n💳 {medio_pago_raw}"

    reply += "\n✅ Registrado"

    # Step 7: Smart suggestions — budget context after every expense
    try:
        from app.services.smart_suggestions import post_expense_suggestions
        period_str = f"{fecha.year}-{fecha.month:02d}"
        suggestions = await post_expense_suggestions(
            db, id_usuario=payload.user_id, id_categoria=id_categoria,
            monto=float(monto), period=period_str, moneda=moneda,
        )
        if suggestions:
            reply += "\n"
            for sug in suggestions[:2]:
                reply += f"\n{sug.mensaje_whatsapp}"
    except Exception as e:
        logger.warning("Smart suggestions failed (non-blocking): %s", e)

    return {
        "status": "created",
        "reply": reply,
        "movimiento_id": created.get("id"),
        "extracted": extracted,
        "categoria": categoria_nombre,
        "subcategoria": subcategoria_nombre,
    }
