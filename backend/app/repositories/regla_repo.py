"""Async repository for ReglaComercio."""
from __future__ import annotations

from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regla_comercio import ReglaComercio
from app.models.categoria import Categoria
from app.models.subcategoria import SubCategoria
from app.utils.normalize import normalize_text


async def list_reglas(
    session: AsyncSession,
    id_usuario: int,
    activa: bool | None = True,
) -> list[dict[str, Any]]:
    conditions = [ReglaComercio.Id_usuario == id_usuario]
    if activa is not None:
        conditions.append(ReglaComercio.Activa == activa)

    stmt = (
        select(
            ReglaComercio,
            Categoria.Nombre.label("cat_nombre"),
            SubCategoria.Nombre_SubCategoria.label("sub_nombre"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == ReglaComercio.Id_Categoria,
            Categoria.Id_usuario == ReglaComercio.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == ReglaComercio.Id_SubCategoria,
            SubCategoria.Id_usuario == ReglaComercio.Id_usuario,
        ))
        .where(and_(*conditions))
        .order_by(ReglaComercio.Prioridad.asc(), ReglaComercio.Patron)
    )

    result = await session.execute(stmt)
    return [_regla_to_dict(row[0], row.cat_nombre or "", row.sub_nombre or "") for row in result.all()]


async def get_regla(
    session: AsyncSession,
    id_usuario: int,
    regla_id: int,
) -> dict[str, Any] | None:
    stmt = (
        select(
            ReglaComercio,
            Categoria.Nombre.label("cat_nombre"),
            SubCategoria.Nombre_SubCategoria.label("sub_nombre"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == ReglaComercio.Id_Categoria,
            Categoria.Id_usuario == ReglaComercio.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == ReglaComercio.Id_SubCategoria,
            SubCategoria.Id_usuario == ReglaComercio.Id_usuario,
        ))
        .where(and_(
            ReglaComercio.Id_usuario == id_usuario,
            ReglaComercio.Id == regla_id,
        ))
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return _regla_to_dict(row[0], row.cat_nombre or "", row.sub_nombre or "")


async def create_regla(
    session: AsyncSession,
    id_usuario: int,
    patron: str,
    id_subcategoria: int,
    id_categoria: int | None = None,
    prioridad: int = 100,
    confianza: str = "MANUAL",
) -> dict[str, Any]:
    # Resolve categoria from subcategoria if not provided
    if id_categoria is None:
        sub_stmt = select(SubCategoria).where(and_(
            SubCategoria.Id_usuario == id_usuario,
            SubCategoria.Id == id_subcategoria,
        ))
        sub = (await session.execute(sub_stmt)).scalar_one_or_none()
        if not sub:
            raise ValueError("Subcategoría no encontrada")
        id_categoria = sub.Id_Categoria

    regla = ReglaComercio(
        Id_usuario=id_usuario,
        Patron=patron.strip(),
        PatronNorm=normalize_text(patron),
        Id_Categoria=id_categoria,
        Id_SubCategoria=id_subcategoria,
        Prioridad=prioridad,
        Confianza=confianza,
    )
    session.add(regla)
    await session.flush()
    return await get_regla(session, id_usuario, regla.Id)


async def update_regla(
    session: AsyncSession,
    id_usuario: int,
    regla_id: int,
    patron: str | None = None,
    id_categoria: int | None = None,
    id_subcategoria: int | None = None,
    prioridad: int | None = None,
    activa: bool | None = None,
) -> dict[str, Any] | None:
    stmt = select(ReglaComercio).where(and_(
        ReglaComercio.Id_usuario == id_usuario,
        ReglaComercio.Id == regla_id,
    ))
    result = await session.execute(stmt)
    regla = result.scalar_one_or_none()
    if not regla:
        return None

    if patron is not None:
        regla.Patron = patron.strip()
        regla.PatronNorm = normalize_text(patron)
    if id_categoria is not None:
        regla.Id_Categoria = id_categoria
    if id_subcategoria is not None:
        regla.Id_SubCategoria = id_subcategoria
        # Auto-resolve categoria from subcategoria
        if id_categoria is None:
            sub_stmt = select(SubCategoria).where(and_(
                SubCategoria.Id_usuario == id_usuario,
                SubCategoria.Id == id_subcategoria,
            ))
            sub = (await session.execute(sub_stmt)).scalar_one_or_none()
            if sub:
                regla.Id_Categoria = sub.Id_Categoria
    if prioridad is not None:
        regla.Prioridad = prioridad
    if activa is not None:
        regla.Activa = activa

    await session.flush()
    return await get_regla(session, id_usuario, regla.Id)


async def delete_regla(
    session: AsyncSession,
    id_usuario: int,
    regla_id: int,
) -> bool:
    stmt = select(ReglaComercio).where(and_(
        ReglaComercio.Id_usuario == id_usuario,
        ReglaComercio.Id == regla_id,
    ))
    result = await session.execute(stmt)
    regla = result.scalar_one_or_none()
    if not regla:
        return False
    await session.delete(regla)
    await session.flush()
    return True


async def resolve_regla(
    session: AsyncSession,
    id_usuario: int,
    comercio_name: str,
) -> dict[str, Any] | None:
    """Find best matching rule for a merchant name."""
    patron_norm = normalize_text(comercio_name)
    if not patron_norm:
        return None

    stmt = (
        select(
            ReglaComercio,
            Categoria.Nombre.label("cat_nombre"),
            SubCategoria.Nombre_SubCategoria.label("sub_nombre"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == ReglaComercio.Id_Categoria,
            Categoria.Id_usuario == ReglaComercio.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == ReglaComercio.Id_SubCategoria,
            SubCategoria.Id_usuario == ReglaComercio.Id_usuario,
        ))
        .where(and_(
            ReglaComercio.Id_usuario == id_usuario,
            ReglaComercio.Activa == True,
            ReglaComercio.PatronNorm == patron_norm,
        ))
        .order_by(ReglaComercio.Prioridad.asc())
        .limit(1)
    )

    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None

    return _regla_to_dict(row[0], row.cat_nombre or "", row.sub_nombre or "")


def _regla_to_dict(regla: ReglaComercio, cat_nombre: str, sub_nombre: str) -> dict[str, Any]:
    return {
        "id": regla.Id,
        "comercio": regla.Patron,
        "patron": regla.Patron,
        "patron_norm": regla.PatronNorm,
        "categoria_id": regla.Id_Categoria,
        "categoria_nombre": cat_nombre,
        "subcategoria_id": regla.Id_SubCategoria,
        "subcategoria_nombre": sub_nombre,
        "prioridad": regla.Prioridad,
        "activa": regla.Activa,
        "confianza": regla.Confianza,
        "timestamp": regla.ActualizadoEn.isoformat() if regla.ActualizadoEn else "",
    }
