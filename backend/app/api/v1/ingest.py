"""Endpoint de ingesta para n8n y fuentes externas."""
import logging
from decimal import Decimal
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_master_key
from app.db.session import get_db
from app.repositories.movimiento_repo import (
    create_movimiento as repo_create,
    get_movimiento_by_origen,
)
from app.repositories.medio_pago_repo import resolve_medio_pago
from app.repositories.regla_repo import create_regla, resolve_regla
from app.repositories.user_repo import get_user_by_gmail
from app.utils.normalize import normalize_text
from app.utils.parse_utils import parse_date_flex, parse_money

logger = logging.getLogger(__name__)
router = APIRouter()

# Defaults para gastos sin regla (según lógica actual de n8n)
DEFAULT_CATEGORIA_ID = 6       # "Otros"
DEFAULT_SUBCATEGORIA_ID = 42   # "Gastos no categorizados"


@router.post("")
async def ingest_movimiento(
    payload: Dict[str, Any],
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingesta de movimiento desde n8n u otra fuente externa.

    Flujo:
    1. Resuelve usuario por gmail
    2. Parsea y valida campos
    3. Normaliza comercio y matchea contra ReglaComercio
    4. Si no hay regla: crea regla AUTO + asigna categoría default
    5. Deduplica por Origen + Origen_Id
    6. Crea movimiento
    """
    # --- 1. Resolver usuario ---
    usuario_gmail = (payload.get("usuario_gmail") or "").strip()
    if not usuario_gmail:
        raise HTTPException(status_code=400, detail="usuario_gmail es requerido")

    user = await get_user_by_gmail(db, usuario_gmail)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuario con gmail '{usuario_gmail}' no encontrado")

    id_usuario = user["id"]

    # --- 2. Parsear campos ---
    fecha = parse_date_flex(payload.get("fecha"))
    if not fecha:
        raise HTTPException(status_code=400, detail="fecha es requerida (YYYY-MM-DD o DD/MM/YYYY)")

    monto = parse_money(payload.get("monto"))
    if monto < 0:
        raise HTTPException(status_code=400, detail="monto debe ser >= 0")

    tipo = str(payload.get("tipo") or "Gasto").strip()
    tipo = "Ingreso" if tipo.lower() == "ingreso" else "Gasto"

    moneda = str(payload.get("moneda") or "ARS").strip() or "ARS"
    descripcion = str(payload.get("descripcion") or "").strip() or None
    comercio_raw = str(payload.get("comercio_raw") or "").strip()
    origen = str(payload.get("origen") or "Gmail").strip()
    origen_id = str(payload.get("origen_id") or "").strip() or None

    # Medios de pago: resolver desde texto o usar IDs directos
    medio_pago_raw = str(payload.get("medio_pago_raw") or "").strip()
    from_email = str(payload.get("from_email") or "").strip()
    asunto = str(payload.get("asunto") or "").strip()

    id_credito_debito = payload.get("id_credito_debito")
    id_medio_pago_final = payload.get("id_medio_pago_final")

    if medio_pago_raw and id_credito_debito is None and id_medio_pago_final is None:
        # Resolver desde texto contra catálogo
        medio_result = await resolve_medio_pago(db, medio_pago_raw, from_email, asunto)
        id_credito_debito = medio_result["id_credito_debito"]
        id_medio_pago_final = medio_result["id_medio_pago_final"]
    else:
        # Usar IDs directos si se pasaron
        if id_credito_debito is not None:
            try:
                id_credito_debito = int(id_credito_debito)
            except (TypeError, ValueError):
                id_credito_debito = None
        if id_medio_pago_final is not None:
            try:
                id_medio_pago_final = int(id_medio_pago_final)
            except (TypeError, ValueError):
                id_medio_pago_final = None

    # --- 3. Deduplicar ---
    # TODO(backlog): reactivar deduplicación cuando n8n envíe el Message ID
    # de Gmail como origen_id en vez del asunto del email.
    # Por ahora deshabilitado porque asuntos genéricos como "Compra aprobada"
    # causaban falsos duplicados.
    origen_id = None  # ignorar hasta que n8n mande un ID real

    # --- 4. Resolver categoría por regla ---
    id_categoria = None
    id_subcategoria = None
    regla_match = None
    regla_creada = False
    comercio_norm = normalize_text(comercio_raw) if comercio_raw else ""

    if comercio_raw:
        regla_match = await resolve_regla(db, id_usuario, comercio_raw)

        if regla_match:
            id_categoria = regla_match["categoria_id"]
            id_subcategoria = regla_match["subcategoria_id"]
        else:
            # Sin regla: asignar defaults y crear regla AUTO
            id_categoria = DEFAULT_CATEGORIA_ID
            id_subcategoria = DEFAULT_SUBCATEGORIA_ID
            try:
                regla_match = await create_regla(
                    db,
                    id_usuario=id_usuario,
                    patron=comercio_raw,
                    id_categoria=DEFAULT_CATEGORIA_ID,
                    id_subcategoria=DEFAULT_SUBCATEGORIA_ID,
                    confianza="AUTO",
                )
                regla_creada = True
            except Exception as e:
                # Si falla crear regla (ej: duplicado), no frenar la ingesta
                logger.warning("No se pudo crear regla AUTO para '%s': %s", comercio_raw, e)

    # Descripcion: incluir comercio si hay
    if comercio_raw and descripcion:
        descripcion = f"{comercio_raw} {descripcion}".strip()
    elif comercio_raw:
        descripcion = comercio_raw

    # --- 5. Crear movimiento ---
    created = await repo_create(
        db,
        id_usuario=id_usuario,
        fecha=fecha,
        tipo=tipo,
        moneda=moneda,
        monto=Decimal(str(round(monto, 2))),
        medio_carga="Gmail",
        descripcion=descripcion,
        id_categoria=id_categoria,
        id_subcategoria=id_subcategoria,
        comercio_id=str(regla_match["id"]) if regla_match else None,
        categoria_manual=False,
        origen=origen,
        origen_id=origen_id,
        id_credito_debito=id_credito_debito,
        id_medio_pago_final=id_medio_pago_final,
    )

    return {
        "status": "creado",
        "movimiento": created,
        "usuario": {
            "id": user["id"],
            "nombre": user.get("Nombre", ""),
            "wpp_entero": user.get("WppEntero", ""),
        },
        "regla": {
            "match": regla_match is not None,
            "creada": regla_creada,
            "categoria": regla_match["categoria_nombre"] if regla_match else "Otros",
            "subcategoria": regla_match["subcategoria_nombre"] if regla_match else "Gastos no categorizados",
        },
    }


@router.post("/batch")
async def ingest_batch(
    payload: Dict[str, Any],
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingesta de múltiples movimientos en un solo request.
    Payload: { "items": [ {...}, {...} ] }
    """
    items: List[Dict[str, Any]] = payload.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="items es requerido y no puede estar vacío")

    if len(items) > 50:
        raise HTTPException(status_code=400, detail="Máximo 50 items por batch")

    results = []
    for i, item in enumerate(items):
        try:
            result = await ingest_movimiento(item, _, db)
            results.append({"index": i, **result})
        except HTTPException as e:
            results.append({"index": i, "status": "error", "detail": e.detail})

    creados = sum(1 for r in results if r.get("status") == "creado")
    duplicados = sum(1 for r in results if r.get("status") == "duplicado")
    errores = sum(1 for r in results if r.get("status") == "error")

    return {
        "total": len(items),
        "creados": creados,
        "duplicados": duplicados,
        "errores": errores,
        "results": results,
    }
