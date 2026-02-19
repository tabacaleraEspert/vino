"""
Endpoints de Movimientos (gastos/ingresos).
Lee/escribe desde Azure SQL cuando MOVIMIENTOS_USE_SQL=True; fallback a Sheets.
"""
from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import set_sheets_context
from app.cache.sheets_cache import invalidate
from app.core.config import settings
from app.core.security import require_user
from app.db.catalog import _get_id_usuario
from app.db.movimientos import (
    list_movimientos as sql_list_movimientos,
    create_movimiento as sql_create_movimiento,
    update_movimiento as sql_update_movimiento,
    get_movimiento as sql_get_movimiento,
    delete_movimiento as sql_delete_movimiento,
)
from app.sheets.registry import get_current_spreadsheet_id
from app.sheets.service import (
    create_movimiento as sheets_create_movimiento,
    get_movimiento_by_id as sheets_get_movimiento,
    list_movimientos_paginated as sheets_list_movimientos_paginated,
    patch_movimiento_by_id as sheets_patch_movimiento,
)
from app.utils.parse_utils import parse_period

router = APIRouter()

USE_SQL = getattr(settings, "MOVIMIENTOS_USE_SQL", True)


def _ensure_items_format(items: list) -> list:
    """Asegura formato MovimientoItem para frontend (id, fecha, tipo, monto, comercio, etc.)."""
    out = []
    for it in items:
        if "id" not in it and "Id" in it:
            it = {**it, "id": str(it.get("Id", ""))}
        out.append(it)
    return out or items


@router.get("")
def list_movimientos(
    period: Optional[str] = Query(default=None, description="YYYY-MM, ej: 2026-02"),
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    tipo: str = Query(default="Gasto"),
    categoria: Optional[str] = None,
    subcategoria: Optional[str] = None,
    comercio: Optional[str] = None,
    moneda: Optional[str] = None,
    min_amount: Optional[float] = Query(default=None),
    max_amount: Optional[float] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Buscar en comercio+descripcion"),
    categoria_id: Optional[str] = None,
    subcategoria_id: Optional[str] = None,
    medio_carga: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=5000),
    sort: str = Query(
        default="timestamp_desc",
        description="timestamp_desc|fecha_desc|monto_desc|monto_asc",
    ),
    user: dict = Depends(require_user),
):
    """
    Listado paginado de movimientos.
    Usa SQL cuando MOVIMIENTOS_USE_SQL=True; sino Sheets.
    """
    if USE_SQL:
        try:
            id_usuario = _get_id_usuario(user)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))

        if period:
            try:
                fd, td = parse_period(period)
                from_date = fd
                to_date = td
            except ValueError:
                pass

        tipo_norm = (tipo or "Gasto").strip()
        if tipo_norm.lower() != "ingreso":
            tipo_norm = "Gasto"
        else:
            tipo_norm = "Ingreso"

        cat_id = int(categoria_id) if categoria_id and str(categoria_id).isdigit() else None
        sub_id = int(subcategoria_id) if subcategoria_id and str(subcategoria_id).isdigit() else None

        offset = (page - 1) * limit
        items, total = sql_list_movimientos(
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
        return {
            "items": _ensure_items_format(items),
            "page": page,
            "limit": limit,
            "total": total,
        }

    set_sheets_context(user)
    try:
        items, total = sheets_list_movimientos_paginated(
            period=period,
            from_date=from_date,
            to_date=to_date,
            tipo=tipo or "Gasto",
            categoria=categoria,
            subcategoria=subcategoria,
            comercio=comercio,
            moneda=moneda,
            user_id=user["sub"],
            min_amount=min_amount,
            max_amount=max_amount,
            q=q,
            categoria_id=categoria_id,
            page=page,
            limit=limit,
            sort=sort,
        )
        return {"items": items, "page": page, "limit": limit, "total": total}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invalidate-cache")
def invalidate_movimientos_cache(user: dict = Depends(require_user)):
    """Invalida cache de Sheets (solo aplica cuando MOVIMIENTOS_USE_SQL=False)."""
    if not USE_SQL:
        set_sheets_context(user)
        sid = get_current_spreadsheet_id()
        invalidate(sid, "movimientos")
    return {"ok": True}


@router.get("/{id}")
def get_movimiento(id: str, user: dict = Depends(require_user)):
    """Obtiene un movimiento por Id."""
    if USE_SQL:
        try:
            id_usuario = _get_id_usuario(user)
            mov_id = int(id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        row = sql_get_movimiento(id_usuario, mov_id)
        if not row:
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        return row

    set_sheets_context(user)
    row = sheets_get_movimiento(id)
    if not row:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return row


@router.post("")
def post_movimiento(payload: Dict[str, Any], user: dict = Depends(require_user)):
    """
    Crea movimiento.
    Usa SQL cuando MOVIMIENTOS_USE_SQL=True.
    Acepta Fecha (YYYY-MM-DD o DD/MM/YYYY), Monto, Comercio, idCategoria/idSubcategoria o Nombre_Categoria/Nombre_SubCategoria.
    """
    if USE_SQL:
        try:
            id_usuario = _get_id_usuario(user)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        try:
            created = sql_create_movimiento(id_usuario, {**payload, "Id_usuario": id_usuario})
            return created
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    set_sheets_context(user)
    try:
        from app.db.regla_comercio import resolve_regla

        payload_with_user = {**payload, "Id_usuario": user["sub"]}
        razon = str(payload.get("Comercio", "") or payload.get("comercio", "")).strip()
        cat_nombre = str(payload.get("Nombre_Categoria", "") or "").strip()
        sub_nombre = str(payload.get("Nombre_SubCategoria", "") or "").strip()
        if razon and (not cat_nombre or not sub_nombre):
            try:
                uid = _get_id_usuario(user)
                resolved = resolve_regla(uid, razon, create_auto_if_no_match=True)
                payload_with_user["Nombre_Categoria"] = resolved.get("nombre_categoria", "")
                payload_with_user["Nombre_SubCategoria"] = resolved.get("nombre_subcategoria", "")
            except (ValueError, Exception):
                pass
        created = sheets_create_movimiento(payload_with_user)
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}")
def patch_movimiento(id: str, payload: Dict[str, Any], user: dict = Depends(require_user)):
    """Actualiza movimiento. Acepta Fecha, Monto, Descripcion, Comercio, Nombre_Categoria, Nombre_SubCategoria, etc."""
    if USE_SQL:
        try:
            id_usuario = _get_id_usuario(user)
            mov_id = int(id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        updated = sql_update_movimiento(id_usuario, mov_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        return updated

    set_sheets_context(user)
    try:
        updated = sheets_patch_movimiento(id, payload)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}")
def put_movimiento(id: str, payload: Dict[str, Any], user: dict = Depends(require_user)):
    """Alias de PATCH para compatibilidad."""
    return patch_movimiento(id, payload, user)


@router.delete("/{id}")
def delete_movimiento(id: str, user: dict = Depends(require_user)):
    """Elimina movimiento."""
    if USE_SQL:
        try:
            id_usuario = _get_id_usuario(user)
            mov_id = int(id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        if not sql_delete_movimiento(id_usuario, mov_id):
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        return {"deleted": True, "id": id}

    raise HTTPException(status_code=501, detail="DELETE solo soportado con MOVIMIENTOS_USE_SQL=True")
