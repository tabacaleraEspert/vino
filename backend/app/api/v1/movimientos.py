"""Endpoints de Movimientos (async, mobile-first)."""
import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.movimiento_repo import (
    list_movimientos as repo_list,
    get_movimiento as repo_get,
    create_movimiento as repo_create,
    update_movimiento as repo_update,
    delete_movimiento as repo_delete,
)
from app.utils.parse_utils import parse_period, parse_date_flex, parse_money

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_movimientos(
    period: Optional[str] = Query(default=None, description="YYYY-MM, ej: 2026-02"),
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    tipo: Optional[str] = Query(default=None, description="Gasto, Ingreso, o vacío para todos"),
    categoria_id: Optional[str] = None,
    subcategoria_id: Optional[str] = None,
    comercio: Optional[str] = None,
    moneda: Optional[str] = None,
    min_amount: Optional[float] = Query(default=None),
    max_amount: Optional[float] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Buscar en comercio+descripcion"),
    medio_carga: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Listado paginado de movimientos (max 100 por página)."""
    if period:
        try:
            fd, td = parse_period(period)
            from_date = fd
            to_date = td
        except ValueError:
            pass

    tipo_norm = None
    if tipo and tipo.strip():
        tipo_norm = "Ingreso" if tipo.strip().lower() == "ingreso" else "Gasto"

    cat_id = int(categoria_id) if categoria_id and str(categoria_id).isdigit() else None
    sub_id = int(subcategoria_id) if subcategoria_id and str(subcategoria_id).isdigit() else None
    offset = (page - 1) * limit

    items, total = await repo_list(
        db,
        id_usuario=id_usuario,
        from_date=from_date,
        to_date=to_date,
        tipo=tipo_norm,
        categoria_id=cat_id,
        subcategoria_id=sub_id,
        medio_carga=medio_carga,
        moneda=moneda,
        comercio=comercio,
        q=q,
        min_amount=min_amount,
        max_amount=max_amount,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "page": page, "limit": limit, "total": total}


@router.post("/invalidate-cache")
async def invalidate_movimientos_cache():
    """No-op: mantenido por compatibilidad con frontend."""
    return {"ok": True}


@router.get("/{id}")
async def get_movimiento(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    row = await repo_get(db, id_usuario, id)
    if not row:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return row


@router.post("")
async def post_movimiento(
    payload: Dict[str, Any],
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Crea movimiento."""
    fecha = parse_date_flex(payload.get("Fecha") or payload.get("fecha"))
    if not fecha:
        raise HTTPException(status_code=400, detail="Fecha es requerida (YYYY-MM-DD o DD/MM/YYYY)")

    monto = parse_money(payload.get("Monto") or payload.get("monto"))
    if monto < 0:
        raise HTTPException(status_code=400, detail="Monto debe ser >= 0")

    tipo = str(payload.get("TipoMovimiento") or payload.get("tipo") or "Gasto").strip()
    tipo = "Ingreso" if tipo.lower() == "ingreso" else "Gasto"

    medio_carga = str(payload.get("MedioCarga") or "Manual").strip() or "Manual"
    moneda = str(payload.get("Moneda") or payload.get("moneda") or "ARS").strip() or "ARS"

    id_cat = payload.get("Id_Categoria") or payload.get("idCategoria")
    id_sub = payload.get("Id_SubCategoria") or payload.get("idSubcategoria")
    if id_cat is not None:
        try:
            id_cat = int(id_cat)
        except (TypeError, ValueError):
            id_cat = None
    if id_sub is not None:
        try:
            id_sub = int(id_sub)
        except (TypeError, ValueError):
            id_sub = None

    descripcion = str(payload.get("Descripcion") or payload.get("descripcion") or "").strip() or None
    comercio = str(payload.get("Comercio") or payload.get("comercio") or "").strip()
    if comercio and descripcion:
        descripcion = f"{comercio} {descripcion}".strip()
    elif comercio:
        descripcion = comercio

    # Resolve category from regla if not provided
    if comercio and id_cat is None and id_sub is None:
        from app.repositories.regla_repo import resolve_regla
        resolved = await resolve_regla(db, id_usuario, comercio)
        if resolved:
            id_cat = resolved["categoria_id"]
            id_sub = resolved["subcategoria_id"]

    # Auto-assign wallet based on currency
    id_billetera = payload.get("Id_Billetera") or payload.get("idBilletera")
    if not id_billetera:
        from sqlalchemy import select, and_
        from app.models.billetera import Billetera
        stmt = select(Billetera.Id).where(and_(
            Billetera.Id_usuario == id_usuario,
            Billetera.Moneda == moneda,
            Billetera.Activa == True,
        )).order_by(Billetera.EsDefault.desc()).limit(1)
        result = await db.execute(stmt)
        wallet_id = result.scalar_one_or_none()
        if wallet_id:
            id_billetera = wallet_id

    # Cuotas (installments)
    cuotas_raw = payload.get("cuotas") or payload.get("cuota_total")
    cuotas = int(cuotas_raw) if cuotas_raw and int(cuotas_raw) > 1 else 1
    monto_total_raw = payload.get("monto_total") or payload.get("MontoTotalCompra")

    if cuotas > 1:
        from dateutil.relativedelta import relativedelta

        monto_total = round(monto, 2)
        if monto_total_raw:
            monto_total = round(float(monto_total_raw), 2)
        monto_cuota = round(monto_total / cuotas, 2)
        base_descripcion = descripcion or ""
        comercio_id = payload.get("ComercioId") or payload.get("comercioId")
        categoria_manual = bool(payload.get("Id_Categoria") or payload.get("idCategoria"))
        origen = str(payload.get("Origen") or "").strip() or None
        origen_id = str(payload.get("Origen_Id") or "").strip() or None

        first_created = None
        for i in range(cuotas):
            cuota_fecha = fecha + relativedelta(months=i)
            cuota_desc = f"{base_descripcion} ({i + 1:02d}/{cuotas:02d})".strip()

            created = await repo_create(
                db,
                id_usuario=id_usuario,
                fecha=cuota_fecha,
                tipo=tipo,
                moneda=moneda,
                monto=Decimal(str(monto_cuota)),
                medio_carga=medio_carga,
                descripcion=cuota_desc,
                id_categoria=id_cat,
                id_subcategoria=id_sub,
                comercio_id=comercio_id,
                categoria_manual=categoria_manual,
                origen=origen,
                origen_id=origen_id,
                cuota_actual=i + 1,
                cuota_total=cuotas,
                monto_total_compra=Decimal(str(monto_total)),
                id_billetera=id_billetera,
            )
            if i == 0:
                first_created = created

        return first_created

    created = await repo_create(
        db,
        id_usuario=id_usuario,
        fecha=fecha,
        tipo=tipo,
        moneda=moneda,
        monto=Decimal(str(round(monto, 2))),
        medio_carga=medio_carga,
        descripcion=descripcion,
        id_categoria=id_cat,
        id_subcategoria=id_sub,
        comercio_id=payload.get("ComercioId") or payload.get("comercioId"),
        categoria_manual=bool(payload.get("Id_Categoria") or payload.get("idCategoria")),
        origen=str(payload.get("Origen") or "").strip() or None,
        origen_id=str(payload.get("Origen_Id") or "").strip() or None,
        id_billetera=id_billetera,
    )
    return created


@router.patch("/{id}")
async def patch_movimiento(
    id: int,
    payload: Dict[str, Any],
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza movimiento."""
    updates: Dict[str, Any] = {}

    if "Fecha" in payload or "fecha" in payload:
        fecha = parse_date_flex(payload.get("Fecha") or payload.get("fecha"))
        if fecha:
            updates["Fecha"] = fecha
    if "Monto" in payload or "monto" in payload:
        monto = parse_money(payload.get("Monto") or payload.get("monto"))
        if monto >= 0:
            updates["Monto"] = Decimal(str(round(monto, 2)))
    if "Descripcion" in payload or "descripcion" in payload:
        updates["Descripcion"] = str(payload.get("Descripcion") or payload.get("descripcion") or "").strip() or None
    if "idCategoria" in payload or "Id_Categoria" in payload:
        id_cat = payload.get("idCategoria") or payload.get("Id_Categoria")
        updates["Id_Categoria"] = int(id_cat) if id_cat is not None else None
        updates["CategoriaManual"] = True
    if "idSubcategoria" in payload or "Id_SubCategoria" in payload:
        id_sub = payload.get("idSubcategoria") or payload.get("Id_SubCategoria")
        updates["Id_SubCategoria"] = int(id_sub) if id_sub is not None else None
        updates["CategoriaManual"] = True
    if "comercioId" in payload or "ComercioId" in payload:
        updates["ComercioId"] = str(payload.get("comercioId") or payload.get("ComercioId") or "").strip() or None
    if "cuotaActual" in payload or "CuotaActual" in payload:
        val = payload.get("cuotaActual") or payload.get("CuotaActual")
        updates["CuotaActual"] = int(val) if val else None
    if "cuotaTotal" in payload or "CuotaTotal" in payload:
        val = payload.get("cuotaTotal") or payload.get("CuotaTotal")
        updates["CuotaTotal"] = int(val) if val else None

    if not updates:
        existing = await repo_get(db, id_usuario, id)
        if not existing:
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        return existing

    updated = await repo_update(db, id_usuario, id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return updated


@router.put("/{id}")
async def put_movimiento(
    id: int,
    payload: Dict[str, Any],
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Alias de PATCH para compatibilidad."""
    return await patch_movimiento(id, payload, id_usuario, db)


@router.delete("/{id}")
async def delete_movimiento(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not await repo_delete(db, id_usuario, id):
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return {"deleted": True, "id": str(id)}
