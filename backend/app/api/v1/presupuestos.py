"""Endpoints de Presupuestos (async)."""
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.presupuesto_repo import (
    list_presupuestos,
    get_presupuesto,
    upsert_presupuesto,
    delete_presupuesto,
)
from app.utils.parse_utils import parse_periodo_mes

router = APIRouter()


class BudgetIn(BaseModel):
    categoryId: str
    subcategoryId: Optional[str] = None
    mes_anio: Optional[str] = None
    amount: float
    period: str = "monthly"
    spent: float = 0


class BudgetPatch(BaseModel):
    categoryId: Optional[str] = None
    subcategoryId: Optional[str] = None
    mes_anio: Optional[str] = None
    amount: Optional[float] = None


def _to_raw(row: dict) -> dict:
    return {
        "id": row["id"],
        "mes_anio": row.get("mes_anio", ""),
        "categoria_id": row.get("categoria_id", ""),
        "categoria_nombre": row.get("categoria_nombre", ""),
        "subcategoria_id": row.get("subcategoria_id", ""),
        "subcategoria_nombre": row.get("subcategoria_nombre", ""),
        "monto": row.get("monto", 0),
    }


@router.get("")
async def get_presupuestos(
    mes_anio: Optional[str] = Query(default=None, alias="mesAño"),
    categoria_id: Optional[str] = Query(default=None),
    subcategoria_id: Optional[str] = Query(default=None),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    periodo_mes = None
    if mes_anio:
        try:
            periodo_mes = parse_periodo_mes(mes_anio)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    rows = await list_presupuestos(db, id_usuario, periodo_mes)

    if categoria_id:
        rows = [r for r in rows if r.get("categoria_id") == str(categoria_id)]
    if subcategoria_id:
        rows = [r for r in rows if r.get("subcategoria_id") == str(subcategoria_id)]

    return [_to_raw(r) for r in rows]


@router.post("")
async def post_presupuesto(
    payload: BudgetIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
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

    row = await upsert_presupuesto(
        db, id_usuario, periodo_mes, Decimal(str(payload.amount)), cat_id, sub_id,
    )
    return {
        "id": row["id"],
        "categoryId": row["categoria_id"],
        "subcategoryId": row["subcategoria_id"] or None,
        "mes_anio": row["mes_anio"],
        "amount": float(row.get("monto", 0)),
        "period": payload.period,
        "spent": payload.spent,
    }


@router.patch("/{id}")
async def patch_presupuesto(
    id: int,
    payload: BudgetPatch,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        pres = await get_presupuesto(db, id_usuario, id)
        if not pres:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        return _to_raw(pres)
    monto = patch.get("amount")
    if monto is not None and monto <= 0:
        raise HTTPException(status_code=400, detail="Monto debe ser mayor a 0")
    # For now, only monto update is supported
    pres = await get_presupuesto(db, id_usuario, id)
    if not pres:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    # Re-upsert with new monto
    if monto is not None:
        from app.models.presupuesto import Presupuesto
        from sqlalchemy import and_, select
        stmt = select(Presupuesto).where(and_(
            Presupuesto.Id_usuario == id_usuario,
            Presupuesto.Id == id,
        ))
        result = await db.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj:
            obj.Monto = Decimal(str(monto))
            await db.flush()
            pres = await get_presupuesto(db, id_usuario, id)
    return _to_raw(pres)


@router.delete("/{id}")
async def delete_presupuesto_endpoint(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not await delete_presupuesto(db, id_usuario, id):
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return {"deleted": True, "id": str(id)}
