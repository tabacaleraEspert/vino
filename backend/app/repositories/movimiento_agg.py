"""Aggregation queries for movimientos — SQL-level SUM/GROUP BY instead of Python loops."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, or_, func, select, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movimiento_orm import Movimiento
from app.models.categoria import Categoria


def _moneda_filter(moneda: str):
    """Build moneda filter — ARS includes NULL/empty (legacy rows)."""
    if moneda == "ARS":
        return or_(
            Movimiento.Moneda == "ARS",
            func.ltrim(func.rtrim(func.coalesce(Movimiento.Moneda, ""))) == "",
        )
    return Movimiento.Moneda == moneda


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
        _moneda_filter(moneda),
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
            _moneda_filter(moneda),
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
        _moneda_filter(moneda),
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
        _moneda_filter(moneda),
    ))
    result = await session.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# New aggregation queries for Smart Suggestions Engine
# ---------------------------------------------------------------------------


async def avg_ticket_por_categoria(
    session: AsyncSession,
    id_usuario: int,
    from_date: date,
    to_date: date,
    id_categoria: int | None = None,
    moneda: str = "ARS",
) -> list[dict[str, Any]]:
    """Average transaction amount per category. Optional filter by single category."""
    conditions = [
        Movimiento.Id_usuario == id_usuario,
        Movimiento.Fecha >= from_date,
        Movimiento.Fecha <= to_date,
        Movimiento.TipoMovimiento == "Gasto",
        _moneda_filter(moneda),
    ]
    if id_categoria is not None:
        conditions.append(Movimiento.Id_Categoria == id_categoria)

    stmt = (
        select(
            Movimiento.Id_Categoria,
            func.coalesce(Categoria.Nombre, "Sin categoría").label("cat_nombre"),
            func.avg(Movimiento.Monto).label("avg_ticket"),
            func.min(Movimiento.Monto).label("min_ticket"),
            func.max(Movimiento.Monto).label("max_ticket"),
            func.count().label("count"),
            func.sum(Movimiento.Monto).label("total"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == Movimiento.Id_Categoria,
            Categoria.Id_usuario == Movimiento.Id_usuario,
        ))
        .where(and_(*conditions))
        .group_by(Movimiento.Id_Categoria, Categoria.Nombre)
    )
    result = await session.execute(stmt)
    return [
        {
            "categoria_id": row.Id_Categoria,
            "categoria": row.cat_nombre or "Sin categoría",
            "avg_ticket": float(row.avg_ticket) if row.avg_ticket else 0,
            "min_ticket": float(row.min_ticket) if row.min_ticket else 0,
            "max_ticket": float(row.max_ticket) if row.max_ticket else 0,
            "count": row.count,
            "total": float(row.total) if row.total else 0,
        }
        for row in result.all()
    ]


async def gastos_categoria_por_periodo(
    session: AsyncSession,
    id_usuario: int,
    id_categoria: int,
    months_back: int = 3,
    moneda: str = "ARS",
) -> list[dict[str, Any]]:
    """Monthly totals for a category over the last N months. For trend analysis."""
    today = date.today()
    start = date(today.year, today.month, 1) - timedelta(days=months_back * 31)
    start = date(start.year, start.month, 1)

    stmt = (
        select(
            func.year(Movimiento.Fecha).label("anio"),
            func.month(Movimiento.Fecha).label("mes"),
            func.sum(Movimiento.Monto).label("total"),
            func.count().label("count"),
        )
        .where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.Id_Categoria == id_categoria,
            Movimiento.Fecha >= start,
            Movimiento.TipoMovimiento == "Gasto",
            _moneda_filter(moneda),
        ))
        .group_by(func.year(Movimiento.Fecha), func.month(Movimiento.Fecha))
        .order_by(func.year(Movimiento.Fecha), func.month(Movimiento.Fecha))
    )
    result = await session.execute(stmt)
    return [
        {
            "periodo": f"{row.anio}-{row.mes:02d}",
            "total": float(row.total),
            "count": row.count,
        }
        for row in result.all()
    ]


async def gastos_por_dia_semana(
    session: AsyncSession,
    id_usuario: int,
    from_date: date,
    to_date: date,
    moneda: str = "ARS",
) -> list[dict[str, Any]]:
    """Spending by day of week. Uses DATEPART for SQL Server."""
    # DATEPART(weekday, Fecha): 1=Sunday..7=Saturday in SQL Server default
    stmt = (
        select(
            func.datepart(literal_column("'weekday'"), Movimiento.Fecha).label("dia_semana"),
            func.sum(Movimiento.Monto).label("total"),
            func.count().label("count"),
        )
        .where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.Fecha >= from_date,
            Movimiento.Fecha <= to_date,
            Movimiento.TipoMovimiento == "Gasto",
            _moneda_filter(moneda),
        ))
        .group_by(func.datepart(literal_column("'weekday'"), Movimiento.Fecha))
    )
    result = await session.execute(stmt)
    return [
        {"dia_semana": row.dia_semana, "total": float(row.total), "count": row.count}
        for row in result.all()
    ]
