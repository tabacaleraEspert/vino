"""Endpoints for managing wallets/accounts (billeteras)."""
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.models.billetera import Billetera
from app.models.movimiento_orm import Movimiento

logger = logging.getLogger(__name__)
router = APIRouter()


class BilleteraIn(BaseModel):
    nombre: str
    moneda: str = "ARS"
    icono: str = ""
    color: str = ""
    saldo_inicial: float = 0


class BilleteraPatch(BaseModel):
    nombre: Optional[str] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    saldo_inicial: Optional[float] = None
    activa: Optional[bool] = None


@router.get("")
async def list_billeteras(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all wallets with current balance."""
    stmt = select(Billetera).where(
        Billetera.Id_usuario == id_usuario
    ).order_by(Billetera.EsDefault.desc(), Billetera.Nombre)
    result = await db.execute(stmt)
    billeteras = result.scalars().all()

    items = []
    for b in billeteras:
        # Calculate balance: saldo_inicial - gastos + ingresos
        gastos_stmt = select(func.coalesce(func.sum(Movimiento.Monto), 0)).where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.Id_Billetera == b.Id,
            Movimiento.TipoMovimiento == "Gasto",
        ))
        ingresos_stmt = select(func.coalesce(func.sum(Movimiento.Monto), 0)).where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.Id_Billetera == b.Id,
            Movimiento.TipoMovimiento == "Ingreso",
        ))

        gastos_result = await db.execute(gastos_stmt)
        ingresos_result = await db.execute(ingresos_stmt)

        gastos = float(gastos_result.scalar_one())
        ingresos = float(ingresos_result.scalar_one())
        saldo = float(b.SaldoInicial) + ingresos - gastos

        items.append({
            "id": b.Id,
            "nombre": b.Nombre,
            "moneda": b.Moneda,
            "icono": b.Icono or ("🇦🇷" if b.Moneda == "ARS" else "🇺🇸" if b.Moneda == "USD" else "💰"),
            "color": b.Color or "#6366f1",
            "saldo_inicial": float(b.SaldoInicial),
            "saldo_actual": round(saldo, 2),
            "gastos_total": round(gastos, 2),
            "ingresos_total": round(ingresos, 2),
            "activa": b.Activa,
            "es_default": b.EsDefault,
        })

    return items


@router.post("")
async def create_billetera(
    payload: BilleteraIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new wallet."""
    b = Billetera(
        Id_usuario=id_usuario,
        Nombre=payload.nombre,
        Moneda=payload.moneda.upper(),
        Icono=payload.icono or ("🇦🇷" if payload.moneda.upper() == "ARS" else "🇺🇸" if payload.moneda.upper() == "USD" else "💰"),
        Color=payload.color or "#6366f1",
        SaldoInicial=Decimal(str(payload.saldo_inicial)),
    )
    db.add(b)
    await db.flush()

    return {
        "id": b.Id,
        "nombre": b.Nombre,
        "moneda": b.Moneda,
        "icono": b.Icono,
        "color": b.Color,
        "saldo_inicial": float(b.SaldoInicial),
    }


@router.patch("/{id}")
async def update_billetera(
    id: int,
    payload: BilleteraPatch,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a wallet."""
    stmt = select(Billetera).where(and_(Billetera.Id == id, Billetera.Id_usuario == id_usuario))
    result = await db.execute(stmt)
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Billetera no encontrada")

    if payload.nombre is not None:
        b.Nombre = payload.nombre
    if payload.icono is not None:
        b.Icono = payload.icono
    if payload.color is not None:
        b.Color = payload.color
    if payload.saldo_inicial is not None:
        b.SaldoInicial = Decimal(str(payload.saldo_inicial))
    if payload.activa is not None:
        b.Activa = payload.activa

    await db.flush()
    return {"id": b.Id, "nombre": b.Nombre, "updated": True}


@router.delete("/{id}")
async def delete_billetera(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a wallet (soft: deactivate)."""
    stmt = select(Billetera).where(and_(Billetera.Id == id, Billetera.Id_usuario == id_usuario))
    result = await db.execute(stmt)
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Billetera no encontrada")

    b.Activa = False
    await db.flush()
    return {"id": b.Id, "deleted": True}
