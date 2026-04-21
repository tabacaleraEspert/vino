"""Async repository for Presupuestos."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.presupuesto import Presupuesto
from app.models.categoria import Categoria
from app.models.subcategoria import SubCategoria


async def list_presupuestos(
    session: AsyncSession,
    id_usuario: int,
    periodo_mes: date | None = None,
) -> list[dict[str, Any]]:
    conditions = [Presupuesto.Id_usuario == id_usuario]
    if periodo_mes:
        conditions.append(Presupuesto.PeriodoMes == periodo_mes)

    stmt = (
        select(
            Presupuesto,
            Categoria.Nombre.label("cat_nombre"),
            SubCategoria.Nombre_SubCategoria.label("sub_nombre"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == Presupuesto.Id_Categoria,
            Categoria.Id_usuario == Presupuesto.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == Presupuesto.Id_SubCategoria,
            SubCategoria.Id_usuario == Presupuesto.Id_usuario,
        ))
        .where(and_(*conditions))
        .order_by(Presupuesto.PeriodoMes.desc())
    )

    result = await session.execute(stmt)
    return [_pres_to_dict(row[0], row.cat_nombre or "", row.sub_nombre or "") for row in result.all()]


async def get_presupuesto(
    session: AsyncSession,
    id_usuario: int,
    pres_id: int,
) -> dict[str, Any] | None:
    stmt = (
        select(
            Presupuesto,
            Categoria.Nombre.label("cat_nombre"),
            SubCategoria.Nombre_SubCategoria.label("sub_nombre"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == Presupuesto.Id_Categoria,
            Categoria.Id_usuario == Presupuesto.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == Presupuesto.Id_SubCategoria,
            SubCategoria.Id_usuario == Presupuesto.Id_usuario,
        ))
        .where(and_(
            Presupuesto.Id_usuario == id_usuario,
            Presupuesto.Id == pres_id,
        ))
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return _pres_to_dict(row[0], row.cat_nombre or "", row.sub_nombre or "")


async def upsert_presupuesto(
    session: AsyncSession,
    id_usuario: int,
    periodo_mes: date,
    monto: Decimal,
    id_categoria: int | None = None,
    id_subcategoria: int | None = None,
) -> dict[str, Any]:
    """Create or update presupuesto (atomic upsert)."""
    # Check for existing
    conditions = [
        Presupuesto.Id_usuario == id_usuario,
        Presupuesto.PeriodoMes == periodo_mes,
    ]
    if id_categoria:
        conditions.append(Presupuesto.Id_Categoria == id_categoria)
    else:
        conditions.append(Presupuesto.Id_Categoria.is_(None))
    if id_subcategoria:
        conditions.append(Presupuesto.Id_SubCategoria == id_subcategoria)
    else:
        conditions.append(Presupuesto.Id_SubCategoria.is_(None))

    stmt = select(Presupuesto).where(and_(*conditions))
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.Monto = monto
        await session.flush()
        return await get_presupuesto(session, id_usuario, existing.Id)
    else:
        pres = Presupuesto(
            Id_usuario=id_usuario,
            PeriodoMes=periodo_mes,
            Id_Categoria=id_categoria,
            Id_SubCategoria=id_subcategoria,
            Monto=monto,
        )
        session.add(pres)
        await session.flush()
        return await get_presupuesto(session, id_usuario, pres.Id)


async def delete_presupuesto(
    session: AsyncSession,
    id_usuario: int,
    pres_id: int,
) -> bool:
    stmt = select(Presupuesto).where(and_(
        Presupuesto.Id_usuario == id_usuario,
        Presupuesto.Id == pres_id,
    ))
    result = await session.execute(stmt)
    pres = result.scalar_one_or_none()
    if not pres:
        return False
    await session.delete(pres)
    await session.flush()
    return True


def _pres_to_dict(pres: Presupuesto, cat_nombre: str, sub_nombre: str) -> dict[str, Any]:
    mes_str = pres.PeriodoMes.strftime("%m/%y") if pres.PeriodoMes else ""
    return {
        "id": pres.Id,
        "mes_anio": mes_str,
        "categoria_id": str(pres.Id_Categoria) if pres.Id_Categoria else "",
        "categoria_nombre": cat_nombre,
        "subcategoria_id": str(pres.Id_SubCategoria) if pres.Id_SubCategoria else "",
        "subcategoria_nombre": sub_nombre,
        "monto": float(pres.Monto),
    }
