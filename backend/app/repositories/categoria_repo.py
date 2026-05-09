"""Async repository for Categorias and SubCategorias."""
from __future__ import annotations

from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categoria import Categoria
from app.models.subcategoria import SubCategoria


async def list_categorias(
    session: AsyncSession,
    id_usuario: int,
) -> list[dict[str, Any]]:
    stmt = (
        select(Categoria)
        .where(Categoria.Id_usuario == id_usuario)
        .order_by(Categoria.Nombre)
    )
    result = await session.execute(stmt)
    return [
        {
            "id": c.Id,
            "nombre": c.Nombre,
            "icon": c.Icon or "📁",
            "color": c.Color or "#6b7280",
            "bucket": c.Bucket or "",
        }
        for c in result.scalars().all()
    ]


async def get_categoria(
    session: AsyncSession,
    id_usuario: int,
    cat_id: int,
) -> dict[str, Any] | None:
    stmt = select(Categoria).where(and_(
        Categoria.Id_usuario == id_usuario,
        Categoria.Id == cat_id,
    ))
    result = await session.execute(stmt)
    c = result.scalar_one_or_none()
    if not c:
        return None
    return {"id": c.Id, "nombre": c.Nombre, "icon": c.Icon, "color": c.Color, "bucket": c.Bucket or ""}


async def create_categoria(
    session: AsyncSession,
    id_usuario: int,
    nombre: str,
    icon: str = "📁",
    color: str = "#6b7280",
    bucket: str = "necesidades",
) -> dict[str, Any]:
    cat = Categoria(Id_usuario=id_usuario, Nombre=nombre, Icon=icon, Color=color, Bucket=bucket)
    session.add(cat)
    await session.flush()
    return {"id": cat.Id, "nombre": cat.Nombre, "icon": cat.Icon, "color": cat.Color, "bucket": cat.Bucket}


async def update_categoria(
    session: AsyncSession,
    id_usuario: int,
    cat_id: int,
    nombre: str | None = None,
    icon: str | None = None,
    color: str | None = None,
    bucket: str | None = None,
) -> dict[str, Any] | None:
    stmt = select(Categoria).where(and_(
        Categoria.Id_usuario == id_usuario,
        Categoria.Id == cat_id,
    ))
    result = await session.execute(stmt)
    cat = result.scalar_one_or_none()
    if not cat:
        return None
    if nombre is not None:
        cat.Nombre = nombre
    if icon is not None:
        cat.Icon = icon
    if color is not None:
        cat.Color = color
    if bucket is not None:
        cat.Bucket = bucket
    await session.flush()
    return {"id": cat.Id, "nombre": cat.Nombre, "icon": cat.Icon, "color": cat.Color, "bucket": cat.Bucket}


async def delete_categoria(
    session: AsyncSession,
    id_usuario: int,
    cat_id: int,
) -> bool:
    stmt = select(Categoria).where(and_(
        Categoria.Id_usuario == id_usuario,
        Categoria.Id == cat_id,
    ))
    result = await session.execute(stmt)
    cat = result.scalar_one_or_none()
    if not cat:
        return False
    await session.delete(cat)
    await session.flush()
    return True


# --- SubCategorias ---

async def list_subcategorias(
    session: AsyncSession,
    id_usuario: int,
    categoria_id: int | None = None,
) -> list[dict[str, Any]]:
    conditions = [SubCategoria.Id_usuario == id_usuario]
    if categoria_id is not None:
        conditions.append(SubCategoria.Id_Categoria == categoria_id)

    stmt = (
        select(SubCategoria)
        .where(and_(*conditions))
        .order_by(SubCategoria.Nombre_SubCategoria)
    )
    result = await session.execute(stmt)
    return [
        {
            "id": s.Id,
            "categoria_id": s.Id_Categoria,
            "nombre": s.Nombre_SubCategoria,
        }
        for s in result.scalars().all()
    ]


async def get_subcategoria(
    session: AsyncSession,
    id_usuario: int,
    sub_id: int,
) -> dict[str, Any] | None:
    stmt = select(SubCategoria).where(and_(
        SubCategoria.Id_usuario == id_usuario,
        SubCategoria.Id == sub_id,
    ))
    result = await session.execute(stmt)
    s = result.scalar_one_or_none()
    if not s:
        return None
    return {"id": s.Id, "categoria_id": s.Id_Categoria, "nombre": s.Nombre_SubCategoria}


async def create_subcategoria(
    session: AsyncSession,
    id_usuario: int,
    categoria_id: int,
    nombre: str,
) -> dict[str, Any]:
    sub = SubCategoria(Id_usuario=id_usuario, Id_Categoria=categoria_id, Nombre_SubCategoria=nombre)
    session.add(sub)
    await session.flush()
    return {"id": sub.Id, "categoria_id": sub.Id_Categoria, "nombre": sub.Nombre_SubCategoria}


async def update_subcategoria(
    session: AsyncSession,
    id_usuario: int,
    sub_id: int,
    nombre: str | None = None,
) -> dict[str, Any] | None:
    stmt = select(SubCategoria).where(and_(
        SubCategoria.Id_usuario == id_usuario,
        SubCategoria.Id == sub_id,
    ))
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        return None
    if nombre is not None:
        sub.Nombre_SubCategoria = nombre
    await session.flush()
    return {"id": sub.Id, "categoria_id": sub.Id_Categoria, "nombre": sub.Nombre_SubCategoria}


async def delete_subcategoria(
    session: AsyncSession,
    id_usuario: int,
    sub_id: int,
) -> bool:
    stmt = select(SubCategoria).where(and_(
        SubCategoria.Id_usuario == id_usuario,
        SubCategoria.Id == sub_id,
    ))
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        return False
    await session.delete(sub)
    await session.flush()
    return True
