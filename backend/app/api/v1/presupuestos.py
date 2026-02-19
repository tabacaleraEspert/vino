"""
Endpoints de Presupuestos desde Azure SQL (multi-tenant por Id_usuario).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Literal, Optional

from app.core.security import require_user
from app.db.catalog import _get_id_usuario
from app.db.presupuestos import (
    list_presupuestos_sql,
    upsert_presupuesto_sql,
    delete_presupuesto_sql,
    get_presupuesto_by_id_sql,
    patch_presupuesto_sql,
)
from app.utils.parse_utils import parse_periodo_mes, periodo_mes_to_mes_anio
from datetime import date

router = APIRouter()


class BudgetIn(BaseModel):
    """Formato frontend existente (categoryId, subcategoryId, mes_anio, amount)."""
    categoryId: str
    subcategoryId: Optional[str] = None
    mes_anio: Optional[str] = None
    amount: float
    period: Literal["monthly", "weekly", "yearly"] = "monthly"
    spent: float = 0


class BudgetPatch(BaseModel):
    categoryId: Optional[str] = None
    subcategoryId: Optional[str] = None
    mes_anio: Optional[str] = None
    amount: Optional[float] = None


def _to_presupuesto_raw(row: dict) -> dict:
    """Formato PresupuestoRaw para frontend."""
    return {
        "id": row["id"],
        "mes_anio": row.get("mes_anio") or row.get("mesAño", ""),
        "categoria_id": row.get("categoria_id", ""),
        "categoria_nombre": row.get("categoria_nombre", ""),
        "subcategoria_id": row.get("subcategoria_id", ""),
        "subcategoria_nombre": row.get("subcategoria_nombre", ""),
        "monto": row.get("monto", str(row.get("Monto", 0))),
    }


@router.get("")
def get_presupuestos(
    mes_anio: Optional[str] = Query(default=None, alias="mesAño"),
    categoria_id: Optional[str] = Query(default=None),
    subcategoria_id: Optional[str] = Query(default=None),
    user: dict = Depends(require_user),
):
    """
    Lista presupuestos del usuario.
    mesAño (MM/YY o YYYY-MM) es el filtro principal. Si no viene, usa mes actual.
    """
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    periodo_mes = None
    if mes_anio:
        try:
            periodo_mes = parse_periodo_mes(mes_anio)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    rows = list_presupuestos_sql(id_usuario, periodo_mes)

    # Filtros opcionales
    if categoria_id:
        rows = [r for r in rows if r.get("categoria_id") == str(categoria_id)]
    if subcategoria_id:
        rows = [r for r in rows if r.get("subcategoria_id") == str(subcategoria_id)]

    return [_to_presupuesto_raw(r) for r in rows]


@router.post("")
def post_presupuesto(payload: BudgetIn, user: dict = Depends(require_user)):
    """
    UPSERT de presupuesto.
    Formato frontend: categoryId, subcategoryId?, mes_anio?, amount.
    mes_anio en MM/YY o YYYY-MM; si no viene, usa mes actual.
    """
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    mes = payload.mes_anio
    if not mes:
        today = date.today()
        mes = f"{today.month:02d}/{today.year % 100:02d}"
    try:
        periodo_mes = parse_periodo_mes(mes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        cat_id = int(payload.categoryId)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="categoryId debe ser un entero")
    sub_id = int(payload.subcategoryId) if payload.subcategoryId else None
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Monto debe ser mayor a 0")

    try:
        row = upsert_presupuesto_sql(id_usuario, periodo_mes, cat_id, sub_id, payload.amount)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "id": row["id"],
        "categoryId": row["categoria_id"],
        "subcategoryId": row["subcategoria_id"] or None,
        "mes_anio": row["mes_anio"],
        "amount": float(row.get("Monto", row.get("monto", 0))),
        "period": payload.period,
        "spent": payload.spent,
    }


@router.patch("/{id}")
def patch_presupuesto(id: str, payload: BudgetPatch, user: dict = Depends(require_user)):
    """Actualiza monto del presupuesto."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        pres = get_presupuesto_by_id_sql(id_usuario, id)
        if not pres:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        return _to_presupuesto_raw(pres)
    monto = patch.get("amount")
    if monto is not None and monto <= 0:
        raise HTTPException(status_code=400, detail="Monto debe ser mayor a 0")
    updated = patch_presupuesto_sql(id_usuario, id, monto=monto)
    if not updated:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return _to_presupuesto_raw(updated)


@router.delete("/{id}")
def delete_presupuesto(id: str, user: dict = Depends(require_user)):
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    if not delete_presupuesto_sql(id_usuario, id):
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return {"deleted": True, "id": id}
