"""WhatsApp endpoints — intake, purchase advice, and more."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_master_key
from app.db.session import get_db
from app.repositories.user_repo import get_user_by_wpp
from app.services.whatsapp_intake import Intent, classify_intent, detect_command
from app.services.purchase_advisor import advise_purchase
from app.services.expense_extractor import extract_expense_from_message
from app.repositories.movimiento_agg import count_gastos_mes as _count_gastos
from app.repositories.categoria_repo import list_categorias as _list_cats

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

    # --- 1b. Onboarding: check if first interaction ---
    from datetime import date, timedelta
    try:
        six_months_ago = date.today() - timedelta(days=180)
        total_movs = await _count_gastos(db, user["id"], six_months_ago, date.today())
        is_new_user = total_movs == 0
    except Exception:
        is_new_user = False

    if is_new_user:
        nombre = user.get("Nombre", "")
        onboarding_msg = (
            f"Hola {nombre}! Soy *Vino*, tu asistente de finanzas personales.\n\n"
            f"Registrá gastos mandándome mensajes como:\n"
            f'_"Almorcé $3.500 en el centro"_\n'
            f'_"Gasté 50k en ropa"_\n'
            f'_"Uber 2500"_\n\n'
            f"También podés preguntarme:\n"
            f'_"Cuánto gasté este mes?"_\n'
            f'_"Puedo comprarme unas zapatillas de 80k?"_\n\n'
            f"Empezá registrando tu primer gasto!"
        )
        return {
            "intent": "ONBOARDING",
            "command_match": True,
            "command_data": {},
            "user": user_summary,
            "raw_body": body,
            "reply": onboarding_msg,
        }

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

    Pipeline: parse (LLM) → execute (DB) → format (pure).
    No more dumping everything to GPT — structured queries with real data.
    """
    from app.repositories.categoria_repo import list_categorias
    from app.services.query_parser import parse_query
    from app.services.query_executor import execute_query
    from app.services.query_formatter import format_query_result

    message = payload.message.strip()
    if not message:
        return {"reply": "No recibí ninguna pregunta."}

    try:
        # Step 1: Parse — LLM extracts structured params
        cats = await list_categorias(db, payload.user_id)
        params = await parse_query(message, cats)

        # Step 2: Execute — call the right DB queries
        result = await execute_query(db, payload.user_id, params)

        # Step 3: Format — build WhatsApp message
        reply = format_query_result(result, user_name=payload.user_name)

    except Exception as e:
        logger.error("WhatsApp query failed: %s", e)
        reply = f"No pude responder tu consulta. Probá de nuevo."

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

    mov_id_raw = created.get("id") or created.get("Id")

    # Step 5b: Handle cuotas and splits
    cuota_actual = extracted.get("cuota_actual")
    cuota_total = extracted.get("cuota_total")
    monto_total_compra = extracted.get("monto_total_compra")
    es_split = extracted.get("es_split", False)
    split_participantes = extracted.get("split_participantes")
    split_nombres = extracted.get("split_nombres", [])

    if cuota_total or es_split:
        try:
            from sqlalchemy import select, and_
            from app.models.movimiento_orm import Movimiento as MovModel
            stmt = select(MovModel).where(MovModel.Id == int(mov_id_raw))
            result = await db.execute(stmt)
            mov_obj = result.scalar_one_or_none()
            if mov_obj:
                if cuota_total:
                    mov_obj.CuotaActual = cuota_actual or 1
                    mov_obj.CuotaTotal = cuota_total
                    if monto_total_compra:
                        mov_obj.MontoTotalCompra = Decimal(str(monto_total_compra))
                if es_split:
                    mov_obj.EsSplit = True
                    if split_participantes:
                        mov_obj.SplitParticipantes = split_participantes
                    mov_obj.SplitTotal = Decimal(str(monto))
                await db.flush()
        except Exception as e:
            logger.warning("Failed to set cuota/split fields: %s", e)

    # Step 5c: Create debts for split
    if es_split and split_participantes and split_participantes > 1:
        try:
            from app.models.deuda import Deuda
            parte_cada_uno = round(monto / split_participantes, 2)
            for i, nombre in enumerate(split_nombres or []):
                if nombre:
                    deuda = Deuda(
                        Id_usuario=payload.user_id,
                        Id_movimiento=int(mov_id_raw),
                        Nombre_deudor=nombre.strip(),
                        Monto=Decimal(str(parte_cada_uno)),
                        Moneda=moneda,
                    )
                    db.add(deuda)
            # If no names but we know count, create placeholders
            if not split_nombres and split_participantes > 1:
                for i in range(split_participantes - 1):  # -1 because user already paid
                    deuda = Deuda(
                        Id_usuario=payload.user_id,
                        Id_movimiento=int(mov_id_raw),
                        Nombre_deudor=f"Persona {i + 1}",
                        Monto=Decimal(str(parte_cada_uno)),
                        Moneda=moneda,
                    )
                    db.add(deuda)
            await db.flush()
        except Exception as e:
            logger.warning("Failed to create split debts: %s", e)

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

    # Cuotas info
    if cuota_total and cuota_total > 1:
        monto_total_fmt = f"${monto_total_compra:,.0f}".replace(",", ".") if monto_total_compra else "?"
        reply += f"\n💳 Cuota {cuota_actual or 1}/{cuota_total} (total: {monto_total_fmt})"

    # Split info
    if es_split and split_participantes and split_participantes > 1:
        parte = round(monto / split_participantes, 2)
        parte_fmt = f"${parte:,.0f}".replace(",", ".")
        deudores = split_participantes - 1
        reply += f"\n👥 Split entre {split_participantes} — cada uno {parte_fmt}"
        reply += f"\n💸 Te deben {deudores} persona{'s' if deudores > 1 else ''}: {f'${parte * deudores:,.0f}'.replace(',', '.')}"
        if split_nombres:
            names = ", ".join(n for n in split_nombres if n)
            if names:
                reply += f"\n   ({names})"

    reply += f"\n\n_Mal categorizado? Respondé:_\n_CAMBIAR {mov_id_raw} + categoría_"

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


# ---------------------------------------------------------------------------
# Ticket photo → register expense
# ---------------------------------------------------------------------------

@router.post("/ticket-photo")
async def register_from_ticket_photo(
    user_id: int = 0,
    file: UploadFile = File(None),
    image_url: str = "",
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Register an expense from a ticket/receipt photo.
    Accepts either a file upload or a Twilio media URL.
    """
    from datetime import date
    from decimal import Decimal
    from app.repositories.categoria_repo import list_categorias, list_subcategorias
    from app.repositories.movimiento_repo import create_movimiento
    from app.repositories.regla_repo import resolve_regla, create_regla
    from app.services.ticket_reader import read_ticket_photo
    from app.services.smart_suggestions import post_expense_suggestions
    from app.utils.parse_utils import parse_date_flex

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id es requerido")

    # Get image bytes — from file upload or URL
    image_bytes = None
    mime_type = "image/jpeg"

    if file and file.filename:
        image_bytes = await file.read()
        mime_type = file.content_type or "image/jpeg"
    elif image_url:
        import httpx
        async with httpx.AsyncClient() as http:
            resp = await http.get(image_url, follow_redirects=True)
            if resp.status_code == 200:
                image_bytes = resp.content
                mime_type = resp.headers.get("content-type", "image/jpeg")

    if not image_bytes:
        return {"status": "error", "reply": "No recibí ninguna imagen."}

    # Load categories
    cats = await list_categorias(db, user_id)
    subs = await list_subcategorias(db, user_id)
    sub_by_cat: dict[int, list] = {}
    for s in subs:
        cid = s.get("categoria_id")
        if cid:
            sub_by_cat.setdefault(cid, []).append(s)
    cats_with_subs = [{**c, "subcategorias": sub_by_cat.get(c["id"], [])} for c in cats]

    # Read ticket with Vision API
    extracted = await read_ticket_photo(image_bytes, mime_type, cats_with_subs)

    if not extracted.get("datos_completos"):
        return {
            "status": "error",
            "reply": "No pude leer el ticket. Probá con una foto más clara o registrá el gasto manualmente.",
            "extracted": extracted,
        }

    monto = extracted.get("monto_total", 0)
    if not monto or monto <= 0:
        return {"status": "error", "reply": "No pude detectar el monto en el ticket."}

    comercio = extracted.get("comercio", "") or ""
    descripcion = extracted.get("descripcion", "") or comercio or "Ticket"
    moneda = extracted.get("moneda", "ARS") or "ARS"
    medio_pago = extracted.get("medio_de_pago", "Efectivo") or "Efectivo"

    # Parse date
    fecha_str = extracted.get("fecha")
    fecha = parse_date_flex(fecha_str) if fecha_str else date.today()
    if not fecha:
        fecha = date.today()

    # Resolve category
    id_categoria = None
    id_subcategoria = None
    categoria_nombre = ""
    subcategoria_nombre = ""

    # Try rule match first
    if comercio:
        regla = await resolve_regla(db, user_id, comercio)
        if regla:
            id_categoria = regla["categoria_id"]
            id_subcategoria = regla["subcategoria_id"]
            categoria_nombre = regla.get("categoria_nombre", "")
            subcategoria_nombre = regla.get("subcategoria_nombre", "")

    # Then GPT suggestion
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

    if not id_categoria:
        id_categoria = 6
        id_subcategoria = 42
        categoria_nombre = "Otros"
        subcategoria_nombre = "Gastos no categorizados"

    # Create movement
    try:
        created = await create_movimiento(
            db, id_usuario=user_id, fecha=fecha, tipo="Gasto",
            moneda=moneda, monto=Decimal(str(round(monto, 2))),
            medio_carga="Ticket", descripcion=descripcion,
            id_categoria=id_categoria, id_subcategoria=id_subcategoria,
            comercio_id=None, categoria_manual=False,
            origen="Ticket", origen_id=None,
            id_credito_debito=None, id_medio_pago_final=None,
        )
    except Exception as e:
        return {"status": "error", "reply": f"Error al registrar: {e}"}

    # Build reply
    monto_fmt = f"${monto:,.0f}".replace(",", ".")
    mov_id = created.get("id") or created.get("Id")

    reply = f"🧾 *{monto_fmt}*"
    if comercio:
        reply += f" en *{comercio}*"
    reply += f"\n📂 {categoria_nombre}"
    if subcategoria_nombre and subcategoria_nombre != "Gastos no categorizados":
        reply += f" / {subcategoria_nombre}"

    # Items detail
    items = extracted.get("items", [])
    if items:
        reply += "\n\n📝 Detalle:"
        for item in items[:5]:
            nombre = item.get("nombre", "")
            precio = item.get("precio", 0)
            if nombre and precio:
                reply += f"\n  · {nombre}: ${precio:,.0f}".replace(",", ".")

    reply += "\n✅ Registrado desde foto"
    reply += f"\n\n_Mal categorizado? Respondé:_\n_CAMBIAR {mov_id} + categoría_"

    # Smart suggestions
    try:
        period_str = f"{fecha.year}-{fecha.month:02d}"
        suggestions = await post_expense_suggestions(
            db, id_usuario=user_id, id_categoria=id_categoria,
            monto=float(monto), period=period_str, moneda=moneda,
        )
        if suggestions:
            reply += "\n"
            for sug in suggestions[:2]:
                reply += f"\n{sug.mensaje_whatsapp}"
    except Exception:
        pass

    return {
        "status": "created",
        "reply": reply,
        "movimiento_id": mov_id,
        "extracted": extracted,
    }


# ---------------------------------------------------------------------------
# Monthly summary for WhatsApp
# ---------------------------------------------------------------------------

class MonthlySummaryRequest(BaseModel):
    user_id: int


@router.post("/monthly-summary")
async def whatsapp_monthly_summary(
    payload: MonthlySummaryRequest,
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate end-of-month summary for WhatsApp.
    Can be triggered by n8n cron or by user request.
    Uses previous month if we're in the first 5 days, otherwise current month.
    """
    from datetime import date
    from app.services.monthly_summary import generate_monthly_summary

    today = date.today()
    # In first 5 days of month, summarize previous month
    if today.day <= 5:
        prev = today.replace(day=1) - timedelta(days=1)
        period = f"{prev.year}-{prev.month:02d}"
    else:
        period = f"{today.year}-{today.month:02d}"

    try:
        result = await generate_monthly_summary(db, payload.user_id, period)
        return {"reply": result["whatsapp_message"], "data": result}
    except Exception as e:
        logger.error("Monthly summary failed: %s", e)
        return {"reply": f"No pude generar el resumen: {e}"}


# ---------------------------------------------------------------------------
# Recategorize — change category of a registered expense
# ---------------------------------------------------------------------------

class RecategorizeRequest(BaseModel):
    user_id: int
    movimiento_id: int
    nueva_categoria: str  # category name (fuzzy matched)


@router.post("/recategorize")
async def recategorize_expense(
    payload: RecategorizeRequest,
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the category of a registered expense.
    Triggered by "CAMBIAR 1234 Transporte" in WhatsApp.
    Also updates/creates a merchant rule for future auto-categorization.
    """
    from sqlalchemy import select, and_
    from app.models.movimiento_orm import Movimiento
    from app.repositories.regla_repo import create_regla, resolve_regla

    # Find the movement
    stmt = select(Movimiento).where(and_(
        Movimiento.Id == payload.movimiento_id,
        Movimiento.Id_usuario == payload.user_id,
    ))
    result = await db.execute(stmt)
    mov = result.scalar_one_or_none()
    if not mov:
        return {"status": "error", "reply": f"No encontré el gasto #{payload.movimiento_id}"}

    # Find matching category by name (fuzzy)
    cats = await _list_cats(db, payload.user_id)
    target = payload.nueva_categoria.lower().strip()
    matched_cat = None
    for c in cats:
        if c["nombre"].lower() == target or target in c["nombre"].lower():
            matched_cat = c
            break

    if not matched_cat:
        cat_names = ", ".join(c["nombre"] for c in cats)
        return {
            "status": "error",
            "reply": f"No encontré la categoría *{payload.nueva_categoria}*.\n\nCategorías disponibles:\n{cat_names}",
        }

    # Update the movement
    old_cat = mov.Id_Categoria
    mov.Id_Categoria = matched_cat["id"]
    mov.CategoriaManual = True
    await db.flush()

    # Update/create merchant rule for future transactions
    comercio = mov.Descripcion or ""
    if comercio:
        try:
            existing_rule = await resolve_regla(db, payload.user_id, comercio)
            if existing_rule:
                from app.models.regla_comercio import ReglaComercio
                regla_stmt = select(ReglaComercio).where(ReglaComercio.Id == existing_rule["id"])
                regla_result = await db.execute(regla_stmt)
                regla = regla_result.scalar_one_or_none()
                if regla:
                    regla.Id_Categoria = matched_cat["id"]
                    regla.Confianza = "MANUAL"
                    await db.flush()
            else:
                await create_regla(
                    db, id_usuario=payload.user_id, patron=comercio,
                    id_categoria=matched_cat["id"], id_subcategoria=None,
                    confianza="MANUAL",
                )
        except Exception as e:
            logger.warning("Rule update failed during recategorize: %s", e)

    reply = (
        f"✏️ Gasto #{payload.movimiento_id} actualizado a *{matched_cat['nombre']}*\n"
        f"Futuros gastos de este comercio se categorizarán automáticamente."
    )

    return {"status": "updated", "reply": reply, "categoria": matched_cat["nombre"]}


# ---------------------------------------------------------------------------
# Unified webhook — replaces n8n orchestration
# ---------------------------------------------------------------------------

from fastapi import Form, Request
import random as _random


def _thinking_message(body: str, user_name: str) -> str:
    """Pick a contextual 'processing' message to send before the real reply."""
    name = user_name.split(" ")[0] if user_name else ""

    # Generic thinking messages
    generic = [
        "Ya te respondo...",
        "Dame un toque...",
        "Dejame ver...",
        "Un segundito...",
        "Procesando...",
    ]

    # Context-aware messages (order matters — check queries before expenses)
    body_lower = body.lower() if body else ""

    if any(w in body_lower for w in ["puedo", "alcanza", "conviene"]):
        options = [
            "Analizando tu presupuesto... 🤔",
            "Dejame ver si te da...",
            "Revisando tus numeros...",
        ]
    elif any(w in body_lower for w in ["cuant", "cuánt", "resum", "como v", "cómo v", "balance", "como me", "cómo me"]):
        options = [
            "Buscando tus datos... 📊",
            "Dejame revisar tus numeros...",
            f"Ya te paso la info{', ' + name if name else ''}...",
            "Consultando... 🔍",
        ]
    elif any(w in body_lower for w in ["gast", "compr", "pagu", "pague", "almor", "cen", "uber", "taxi", "nafta", "delivery"]):
        has_number = any(c.isdigit() for c in body)
        if has_number:
            options = [
                "Anotando tu gasto... ✍️",
                "Ya lo registro...",
                "Dejame anotarlo... 📝",
                f"Recibido{', ' + name if name else ''}, ya lo proceso...",
            ]
        else:
            options = generic
    else:
        options = generic

    return _random.choice(options)


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Unified Twilio webhook — receives WhatsApp messages, classifies intent,
    executes the action, and sends the response back via Twilio.

    Replaces the n8n orchestration layer entirely.
    """
    from app.services.twilio_client import send_whatsapp

    # Parse Twilio form-encoded webhook
    form = await request.form()
    wpp_from = str(form.get("From", "")).strip()
    body = str(form.get("Body", "")).strip()
    button_payload = form.get("ButtonPayload")
    media_url = form.get("MediaUrl0")

    if not wpp_from:
        return {"status": "ignored", "reason": "no From"}

    # --- 1. Resolve user ---
    user = await get_user_by_wpp(db, wpp_from)
    if not user:
        logger.warning("webhook: unknown sender %s", wpp_from)
        return {"status": "ignored", "reason": "unknown user"}

    user_id = user["id"]
    user_name = user.get("Nombre", "")

    # --- 2. Onboarding check ---
    from datetime import date, timedelta
    try:
        six_months_ago = date.today() - timedelta(days=180)
        total_movs = await _count_gastos(db, user_id, six_months_ago, date.today())
        is_new_user = total_movs == 0
    except Exception:
        is_new_user = False

    if is_new_user:
        reply = (
            f"Hola {user_name}! Soy *Vino*, tu asistente de finanzas personales.\n\n"
            f"Registra gastos mandandome mensajes como:\n"
            f'_"Almorce $3.500 en el centro"_\n'
            f'_"Gaste 50k en ropa"_\n'
            f'_"Uber 2500"_\n\n'
            f"Tambien podes preguntarme:\n"
            f'_"Cuanto gaste este mes?"_\n'
            f'_"Puedo comprarme unas zapatillas de 80k?"_\n\n'
            f"Empeza registrando tu primer gasto!"
        )
        await send_whatsapp(wpp_from, reply)
        return {"status": "onboarding"}

    # --- 3. Handle media (photo or audio) ---
    if media_url:
        media_type = str(form.get("MediaContentType0", "")).lower()

        # Audio → transcribe with Whisper, then process as text
        if "audio" in media_type or "ogg" in media_type:
            await send_whatsapp(wpp_from, _random.choice([
                "Escuchando tu audio... 🎧",
                "Procesando tu mensaje de voz...",
                "Ya escucho y te respondo...",
            ]))
            try:
                import httpx
                from openai import AsyncOpenAI
                from app.core.config import settings as _settings

                # Download audio from Twilio
                async with httpx.AsyncClient() as http:
                    auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    audio_resp = await http.get(str(media_url), auth=auth, follow_redirects=True, timeout=15)
                    audio_bytes = audio_resp.content

                # Transcribe with Whisper
                client = AsyncOpenAI(api_key=_settings.OPENAI_API_KEY)
                import io
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = "audio.ogg"
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es",
                )
                body = transcript.text.strip()
                logger.info("Audio transcribed: %r", body[:100])
                if not body:
                    await send_whatsapp(wpp_from, "No pude entender el audio. Proba de nuevo.")
                    return {"status": "audio_empty"}
                # Fall through to text processing below
            except Exception as e:
                logger.error("Audio transcription failed: %s", e)
                await send_whatsapp(wpp_from, "No pude procesar el audio. Proba mandando un texto.")
                return {"status": "audio_error"}

        # Image → ticket/receipt OCR
        elif "image" in media_type:
            try:
                result = await register_from_ticket_photo(
                    user_id=user_id,
                    image_url=str(media_url),
                    db=db,
                )
                reply = result.get("reply", "No pude leer la imagen.")
                await send_whatsapp(wpp_from, reply)
                return {"status": "ticket_processed"}
            except Exception as e:
                logger.error("Ticket photo failed: %s", e)
                await send_whatsapp(wpp_from, "No pude procesar la imagen. Proba con una foto mas clara.")
                return {"status": "ticket_error"}

        else:
            await send_whatsapp(wpp_from, "Solo puedo procesar fotos de tickets y mensajes de audio.")
            return {"status": "unsupported_media"}

    if not body:
        return {"status": "ignored", "reason": "empty body"}

    # --- 3b. Send "thinking" message ---
    thinking = _thinking_message(body, user_name)
    await send_whatsapp(wpp_from, thinking)

    # --- 4. Detect command ---
    cmd = detect_command(body, str(button_payload) if button_payload else None)
    if cmd:
        intent = cmd["intent"]
        command_data = cmd["command_data"]
    else:
        # --- 5. Classify with AI ---
        intent = await classify_intent(body)
        command_data = {}

    # --- 6. Route by intent ---
    reply = ""
    try:
        if intent == Intent.DATA:
            result = await register_expense(
                payload=RegisterExpenseRequest(user_id=user_id, message=body, user_name=user_name),
                db=db,
            )
            reply = result.get("reply", "Registrado.")

        elif intent == Intent.QUERY:
            result = await whatsapp_query(
                payload=QueryRequest(user_id=user_id, message=body, user_name=user_name),
                db=db,
            )
            reply = result.get("reply", "No pude responder.")

        elif intent == Intent.SUGERENCIAS:
            result = await suggest_purchase(
                payload=PurchaseAdviceRequest(user_id=user_id, message=body, user_name=user_name),
                db=db,
            )
            reply = result.get("reply", "No pude analizar.")

        elif intent == Intent.WEEKLY_RESUME:
            result = await whatsapp_monthly_summary(
                payload=MonthlySummaryRequest(user_id=user_id),
                db=db,
            )
            reply = result.get("reply", "No pude generar el resumen.")

        elif intent == Intent.CATEGORIZACION:
            mov_id = command_data.get("movimiento_id")
            nueva_cat = command_data.get("nueva_categoria", "")
            if mov_id and nueva_cat:
                result = await recategorize_expense(
                    payload=RecategorizeRequest(
                        user_id=user_id,
                        movimiento_id=mov_id,
                        nueva_categoria=nueva_cat,
                    ),
                    db=db,
                )
                reply = result.get("reply", "Actualizado.")
            elif mov_id:
                # Just CATEGORIZAR <id> — list categories
                cats = await _list_cats(db, user_id)
                cat_names = ", ".join(c["nombre"] for c in cats)
                reply = (
                    f"Para cambiar la categoria del gasto #{mov_id}, "
                    f"manda:\n_CAMBIAR {mov_id} <categoria>_\n\n"
                    f"Categorias: {cat_names}"
                )
            else:
                reply = "Usa: _CAMBIAR <id> <categoria>_"

        elif intent == Intent.PRESUPUESTO:
            # Query about budget
            result = await whatsapp_query(
                payload=QueryRequest(user_id=user_id, message=body, user_name=user_name),
                db=db,
            )
            reply = result.get("reply", "No pude responder.")

        elif intent == Intent.OTHER:
            # Conversational fallback — respond as financial assistant with context
            try:
                from datetime import date as _date
                from app.api.v1.chat import _build_context, _SYSTEM_PROMPT
                from openai import AsyncOpenAI
                from app.core.config import settings as _settings

                today = _date.today()
                period = f"{today.year}-{today.month:02d}"
                context = await _build_context(db, user_id, period)
                system = _SYSTEM_PROMPT.replace("{context}", context)
                system += (
                    "\n\nSi el mensaje no tiene que ver con finanzas, responde "
                    "amablemente y sugeri que te pregunte sobre sus gastos, "
                    "presupuesto o que registre un gasto."
                )

                client = AsyncOpenAI(api_key=_settings.OPENAI_API_KEY)
                response = await client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": body},
                    ],
                    max_completion_tokens=300,
                    temperature=0.7,
                )
                reply = response.choices[0].message.content or ""
            except Exception as e:
                logger.error("OTHER conversational fallback failed: %s", e)
                reply = (
                    f"Hola {user_name}! Soy tu asistente de finanzas.\n\n"
                    f"Podes:\n"
                    f'• Registrar gastos: _"Gaste 5000 en cafe"_\n'
                    f'• Consultar: _"Cuanto gaste este mes?"_\n'
                    f'• Pedir consejo: _"Puedo comprarme unas zapas de 80k?"_'
                )

        else:
            reply = "No entendi. Proba de nuevo."

    except Exception as e:
        logger.error("webhook intent=%s error: %s", intent, e)
        reply = "Hubo un error procesando tu mensaje. Proba de nuevo."

    # --- 7. Send reply ---
    if reply:
        await send_whatsapp(wpp_from, reply)

    return {"status": "ok", "intent": str(intent)}
