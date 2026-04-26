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
from app.repositories.categoria_repo import list_categorias
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


# ---------------------------------------------------------------------------
# Regla 50/30/20 — auto-asignación
# ---------------------------------------------------------------------------

# Mapping of category names (lowercase) to 50/30/20 buckets.
# "necesidades" = 50%, "deseos" = 30%, "ahorro" = 20%
_BUCKET_MAP: dict[str, str] = {
    # Necesidades (50%)
    "vivienda": "necesidades",
    "alimentacion": "necesidades",
    "alimentación": "necesidades",
    "transporte": "necesidades",
    "servicios": "necesidades",
    "salud": "necesidades",
    "educacion": "necesidades",
    "educación": "necesidades",
    "impuestos": "necesidades",
    # Deseos (30%)
    "entretenimiento": "deseos",
    "delivery": "deseos",
    "restaurantes": "deseos",
    "suscripciones": "deseos",
    "ropa": "deseos",
    "compras": "deseos",
    "vacaciones": "deseos",
    "ocio": "deseos",
    "hobbies": "deseos",
    "tecnologia": "deseos",
    "tecnología": "deseos",
    "belleza": "deseos",
    "mascotas": "deseos",
    "regalos": "deseos",
    # Ahorro (20%)
    "ahorro": "ahorro",
    "inversiones": "ahorro",
    "deudas": "ahorro",
    "emergencias": "ahorro",
}

_BUCKET_PCT = {"necesidades": 0.50, "deseos": 0.30, "ahorro": 0.20}


class AutoAssignIn(BaseModel):
    total: float
    mes_anio: Optional[str] = None


@router.post("/auto-assign")
async def auto_assign_budgets(
    payload: AutoAssignIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-asigna presupuestos basado en la regla 50/30/20.

    - 50% Necesidades (vivienda, alimentación, transporte, servicios, salud)
    - 30% Deseos (entretenimiento, delivery, ropa, suscripciones)
    - 20% Ahorro (ahorro, inversiones, deudas)

    Distribuye equitativamente dentro de cada bucket entre las categorías
    del usuario que pertenezcan a ese bucket.
    """
    if payload.total <= 0:
        raise HTTPException(status_code=400, detail="El total debe ser mayor a 0")

    mes = payload.mes_anio
    if not mes:
        today = date.today()
        mes = f"{today.month:02d}/{today.year % 100:02d}"
    try:
        periodo_mes = parse_periodo_mes(mes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get user's categories
    cats = await list_categorias(db, id_usuario)
    if not cats:
        raise HTTPException(status_code=400, detail="No hay categorías configuradas")

    # Classify categories into buckets
    buckets: dict[str, list[dict]] = {"necesidades": [], "deseos": [], "ahorro": []}
    uncategorized = []
    for cat in cats:
        nombre = (cat.get("nombre", "") or "").strip().lower()
        bucket = _BUCKET_MAP.get(nombre)
        if bucket:
            buckets[bucket].append(cat)
        else:
            uncategorized.append(cat)

    # Assign uncategorized to "deseos" as fallback
    buckets["deseos"].extend(uncategorized)

    # Distribute budget
    total = payload.total
    created = []
    distribution = []

    for bucket_name, pct in _BUCKET_PCT.items():
        bucket_cats = buckets[bucket_name]
        bucket_total = total * pct
        if not bucket_cats:
            continue
        per_cat = round(bucket_total / len(bucket_cats), 2)
        for cat in bucket_cats:
            row = await upsert_presupuesto(
                db, id_usuario, periodo_mes,
                Decimal(str(per_cat)),
                id_categoria=cat["id"],
            )
            created.append(_to_raw(row))
            distribution.append({
                "categoria": cat.get("nombre", ""),
                "bucket": bucket_name,
                "pct_bucket": f"{int(pct * 100)}%",
                "monto": per_cat,
            })

    return {
        "total": total,
        "regla": "50/30/20",
        "mes_anio": mes,
        "presupuestos_creados": len(created),
        "distribucion": distribution,
        "presupuestos": created,
    }
