from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import set_sheets_context
from app.core.security import require_user
from app.sheets.service import (
    create_movimiento,
    get_movimiento_by_id,
    list_movimientos_paginated as svc_list_movimientos_paginated,
    patch_movimiento_by_id,
)

router = APIRouter()


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
    user_id viene del JWT (id del usuario en MaestroUsuarios).
    """
    set_sheets_context(user)
    try:
        items, total = svc_list_movimientos_paginated(
            period=period,
            from_date=from_date,
            to_date=to_date,
            tipo=tipo,
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
        return {
            "items": items,
            "page": page,
            "limit": limit,
            "total": total,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}")
def get_movimiento(id: str, user: dict = Depends(require_user)):
    set_sheets_context(user)
    row = get_movimiento_by_id(id)
    if not row:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return row


@router.post("")
def post_movimiento(payload: Dict[str, Any], user: dict = Depends(require_user)):
    """
    Crea movimiento. Id_usuario se setea automáticamente desde el usuario autenticado.
    payload: "Fecha", "Tipo de Movimiento", "Moneda", "Monto", ...
    """
    set_sheets_context(user)
    try:
        payload_with_user = {**payload, "Id_usuario": user["sub"]}
        created = create_movimiento(payload_with_user)
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}")
def patch_movimiento(id: str, payload: Dict[str, Any], user: dict = Depends(require_user)):
    """
    payload: {"Monto": "5000", "Descripcion": "..." } etc.
    No se permite cambiar "Id".
    """
    set_sheets_context(user)
    try:
        updated = patch_movimiento_by_id(id, payload)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
