"""Endpoints for managing split debts (me deben / pagué yo)."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.models.deuda import Deuda

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_deudas(
    pagado: bool | None = None,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all debts. Filter by pagado=true/false."""
    conditions = [Deuda.Id_usuario == id_usuario]
    if pagado is not None:
        conditions.append(Deuda.Pagado == pagado)

    stmt = select(Deuda).where(and_(*conditions)).order_by(Deuda.Timestamp.desc())
    result = await db.execute(stmt)
    deudas = result.scalars().all()

    return [
        {
            "id": d.Id,
            "movimiento_id": d.Id_movimiento,
            "nombre": d.Nombre_deudor,
            "monto": float(d.Monto),
            "moneda": d.Moneda,
            "pagado": d.Pagado,
            "fecha": d.Timestamp.isoformat() if d.Timestamp else None,
            "fecha_pago": d.FechaPago.isoformat() if d.FechaPago else None,
        }
        for d in deudas
    ]


@router.get("/summary")
async def deudas_summary(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Summary: total owed, by person."""
    stmt = (
        select(
            Deuda.Nombre_deudor,
            func.sum(Deuda.Monto).label("total"),
            func.count().label("count"),
        )
        .where(and_(Deuda.Id_usuario == id_usuario, Deuda.Pagado == False))
        .group_by(Deuda.Nombre_deudor)
        .order_by(func.sum(Deuda.Monto).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    total = sum(float(r.total) for r in rows)
    return {
        "total_pendiente": total,
        "personas": [
            {"nombre": r.Nombre_deudor, "total": float(r.total), "count": r.count}
            for r in rows
        ],
    }


@router.patch("/{id}/pagar")
async def marcar_pagado(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a debt as paid."""
    stmt = select(Deuda).where(and_(Deuda.Id == id, Deuda.Id_usuario == id_usuario))
    result = await db.execute(stmt)
    deuda = result.scalar_one_or_none()
    if not deuda:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")

    deuda.Pagado = True
    deuda.FechaPago = datetime.utcnow()
    await db.flush()

    return {"id": deuda.Id, "pagado": True, "nombre": deuda.Nombre_deudor, "monto": float(deuda.Monto)}


@router.delete("/{id}")
async def delete_deuda(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a debt record."""
    stmt = select(Deuda).where(and_(Deuda.Id == id, Deuda.Id_usuario == id_usuario))
    result = await db.execute(stmt)
    deuda = result.scalar_one_or_none()
    if not deuda:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")

    await db.delete(deuda)
    await db.flush()
    return {"deleted": True, "id": id}
