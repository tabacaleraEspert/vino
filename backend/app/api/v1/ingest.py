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
    find_duplicate_cross_source,
)
from app.repositories.medio_pago_repo import resolve_medio_pago
from app.repositories.regla_repo import create_regla, resolve_regla
from app.repositories.user_repo import get_user_by_gmail
from app.repositories.categoria_repo import list_categorias, list_subcategorias
from app.utils.normalize import normalize_text
from app.utils.parse_utils import parse_date_flex, parse_money

logger = logging.getLogger(__name__)
router = APIRouter()

async def _get_default_category(db, id_usuario: int, tipo: str = "Gasto") -> tuple[int | None, int | None]:
    """Get the user's default category + subcategory for the given tipo."""
    from sqlalchemy import select, and_
    from app.models.categoria import Categoria
    from app.models.subcategoria import SubCategoria

    if tipo == "Ingreso":
        # Look for "Ingresos" category with tipo="Ingreso"
        stmt = select(Categoria).where(and_(
            Categoria.Id_usuario == id_usuario,
            Categoria.Tipo == "Ingreso",
        )).limit(1)
        result = await db.execute(stmt)
        cat = result.scalar_one_or_none()
        if not cat:
            return None, None
        # Prefer "Ingresos no categorizados" subcategory
        stmt2 = select(SubCategoria.Id).where(and_(
            SubCategoria.Id_usuario == id_usuario,
            SubCategoria.Id_Categoria == cat.Id,
            SubCategoria.Nombre_SubCategoria.in_(["Ingresos no categorizados"]),
        )).limit(1)
        result2 = await db.execute(stmt2)
        sub_id = result2.scalar_one_or_none()
        if not sub_id:
            # Fallback: first subcategory
            stmt3 = select(SubCategoria.Id).where(and_(
                SubCategoria.Id_usuario == id_usuario,
                SubCategoria.Id_Categoria == cat.Id,
            )).limit(1)
            result3 = await db.execute(stmt3)
            sub_id = result3.scalar_one_or_none()
        return cat.Id, sub_id
    else:
        stmt = select(Categoria).where(and_(
            Categoria.Id_usuario == id_usuario,
            Categoria.Nombre.in_(["Otros", "otros"]),
        )).limit(1)
        result = await db.execute(stmt)
        cat = result.scalar_one_or_none()
        if not cat:
            return None, None
        stmt2 = select(SubCategoria.Id).where(and_(
            SubCategoria.Id_usuario == id_usuario,
            SubCategoria.Id_Categoria == cat.Id,
        )).limit(1)
        result2 = await db.execute(stmt2)
        sub_id = result2.scalar_one_or_none()
        return cat.Id, sub_id


@router.post("")
async def ingest_movimiento(
    payload: Dict[str, Any],
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """HTTP endpoint for ingest — thin wrapper around process_ingest."""
    return await process_ingest(db, payload)


async def process_ingest(db: AsyncSession, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core ingest logic — callable from HTTP endpoint and internal services (Gmail poller).

    Raises HTTPException on validation errors. Returns result dict on success.
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
    if origen_id:
        existing = await get_movimiento_by_origen(db, id_usuario, origen, origen_id)
        if existing:
            return {
                "status": "duplicado",
                "movimiento": existing,
                "usuario": {
                    "id": user["id"],
                    "nombre": user.get("Nombre", ""),
                    "wpp_entero": user.get("WppEntero", ""),
                },
            }

    # --- 3b. Cross-source dedup (bank + MercadoPago for same purchase) ---
    if monto > 0 and fecha:
        cross_dup = await find_duplicate_cross_source(
            db, id_usuario, monto=round(monto, 2), fecha=fecha,
            moneda=moneda, window_minutes=10,
        )
        if cross_dup:
            logger.info("Cross-source duplicate detected: mov %s matches existing %s", comercio_raw, cross_dup.get("id"))
            return {
                "status": "duplicado_cross",
                "movimiento": cross_dup,
                "usuario": {
                    "id": user["id"],
                    "nombre": user.get("Nombre", ""),
                    "wpp_entero": user.get("WppEntero", ""),
                },
            }

    # --- 4. Resolver categoría por regla ---
    id_categoria = None
    id_subcategoria = None
    regla_match = None
    regla_creada = False
    comercio_norm = normalize_text(comercio_raw) if comercio_raw else ""

    if comercio_raw:
        regla_match = await resolve_regla(db, id_usuario, comercio_raw, tipo=tipo)

        if regla_match:
            id_categoria = regla_match["categoria_id"]
            id_subcategoria = regla_match["subcategoria_id"]
        else:
            # Sin regla: asignar categoría por defecto (usuario categoriza después)
            id_categoria, id_subcategoria = await _get_default_category(db, id_usuario, tipo)

            try:
                regla_match = await create_regla(
                    db,
                    id_usuario=id_usuario,
                    patron=comercio_raw,
                    id_categoria=id_categoria,
                    id_subcategoria=id_subcategoria,
                    confianza="AUTO",
                    tipo_movimiento=tipo,
                )
                regla_creada = True
            except Exception as e:
                logger.warning("No se pudo crear regla para '%s': %s", comercio_raw, e)

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
        comercio_raw=comercio_raw or None,
        comercio_norm=normalize_text(comercio_raw) if comercio_raw else None,
        regla_comercio_id=regla_match["id"] if regla_match else None,
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
            result = await process_ingest(db, item)
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
