"""Async repository for Users."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_nombre(
    session: AsyncSession,
    nombre: str,
) -> dict[str, Any] | None:
    stmt = select(User).where(User.Nombre == nombre)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None
    return _user_to_dict(user)


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> dict[str, Any] | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None
    return _user_to_dict(user)


async def create_user(
    session: AsyncSession,
    nombre: str,
    password_hash: str,
    apellido: str | None = None,
    gmail: str | None = None,
) -> dict[str, Any]:
    # Check for existing
    existing = await get_user_by_nombre(session, nombre)
    if existing:
        raise ValueError(f"Ya existe un usuario con nombre '{nombre}'")

    user = User(
        Nombre=nombre,
        PasswordHash=password_hash,
        Apellido=apellido,
        gmail=gmail,
    )
    session.add(user)
    await session.flush()
    return _user_to_dict(user)


def _user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "Id": user.id,
        "Nombre": user.Nombre,
        "Apellido": user.Apellido or "",
        "gmail": user.gmail or "",
        "PasswordHash": user.PasswordHash or "",
        "ID_Sheets": user.ID_Sheets or "",
    }
