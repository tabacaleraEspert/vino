"""Aggregation queries for movimientos — SQL-level SUM/GROUP BY instead of Python loops."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movimiento_orm import Movimiento
from app.models.categoria import Categoria


async def sum_gastos_mes(
    session: AsyncSession,
    id_usuario: int,
    from_date: date,
    to_date: date,
    moneda: str = "ARS",
) -> float:
    """Sum all expenses for a period. Single SQL query, no Python loop."""
    stmt = select(func.coalesce(func.sum(Movimiento.Monto), 0)).where(and_(
        Movimiento.Id_usuario == id_usuario,
        Movimiento.Fecha >= from_date,
        Movimiento.Fecha <= to_date,
        Movimiento.TipoMovimiento == "Gasto",
        Movimiento.Moneda == moneda,
    ))
    result = await session.execute(stmt)
    return float(result.scalar_one())


async def gastos_por_categoria(
    session: AsyncSession,
    id_usuario: int,
    from_date: date,
    to_date: date,
    moneda: str = "ARS",
    top: int = 10,
) -> list[dict[str, Any]]:
    """
    Group expenses by category for a period.
    Returns: [{categoria: name, categoria_id: id, total: float, count: int}, ...]
    Single SQL query with GROUP BY.
    """
    stmt = (
        select(
            Movimiento.Id_Categoria,
            func.coalesce(Categoria.Nombre, "Sin categoría").label("cat_nombre"),
            func.sum(Movimiento.Monto).label("total"),
            func.count().label("count"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == Movimiento.Id_Categoria,
            Categoria.Id_usuario == Movimiento.Id_usuario,
        ))
        .where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.Fecha >= from_date,
            Movimiento.Fecha <= to_date,
            Movimiento.TipoMovimiento == "Gasto",
            Movimiento.Moneda == moneda,
        ))
        .group_by(Movimiento.Id_Categoria, Categoria.Nombre)
        .order_by(func.sum(Movimiento.Monto).desc())
        .limit(top)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        {
            "categoria_id": row.Id_Categoria,
            "categoria": row.cat_nombre or "Sin categoría",
            "total": float(row.total),
            "count": row.count,
        }
        for row in rows
    ]


async def mayor_gasto_mes(
    session: AsyncSession,
    id_usuario: int,
    from_date: date,
    to_date: date,
    moneda: str = "ARS",
) -> float:
    """Get the largest single expense in the period."""
    stmt = select(func.coalesce(func.max(Movimiento.Monto), 0)).where(and_(
        Movimiento.Id_usuario == id_usuario,
        Movimiento.Fecha >= from_date,
        Movimiento.Fecha <= to_date,
        Movimiento.TipoMovimiento == "Gasto",
        Movimiento.Moneda == moneda,
    ))
    result = await session.execute(stmt)
    return float(result.scalar_one())


async def count_gastos_mes(
    session: AsyncSession,
    id_usuario: int,
    from_date: date,
    to_date: date,
    moneda: str = "ARS",
) -> int:
    """Count expenses in the period."""
    stmt = select(func.count()).where(and_(
        Movimiento.Id_usuario == id_usuario,
        Movimiento.Fecha >= from_date,
        Movimiento.Fecha <= to_date,
        Movimiento.TipoMovimiento == "Gasto",
        Movimiento.Moneda == moneda,
    ))
    result = await session.execute(stmt)
    return result.scalar_one()
