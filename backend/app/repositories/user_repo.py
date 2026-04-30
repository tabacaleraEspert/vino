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


async def get_user_by_gmail(
    session: AsyncSession,
    gmail: str,
) -> dict[str, Any] | None:
    stmt = select(User).where(User.gmail == gmail)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None
    return _user_to_dict(user)


async def get_user_by_wpp(
    session: AsyncSession,
    wpp_entero: str,
) -> dict[str, Any] | None:
    stmt = select(User).where(User.WppEntero == wpp_entero)
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
    password_hash: str | None = None,
    apellido: str | None = None,
    gmail: str | None = None,
    whatsapp: str | None = None,
    wpp_entero: str | None = None,
) -> dict[str, Any]:
    # Check for existing
    existing = await get_user_by_nombre(session, nombre)
    if existing:
        raise ValueError(f"Ya existe un usuario con nombre '{nombre}'")

    # Check WPP not taken
    if wpp_entero:
        existing_wpp = await get_user_by_wpp(session, wpp_entero)
        if existing_wpp:
            raise ValueError("Ese número de WhatsApp ya está vinculado a otra cuenta")

    user = User(
        Nombre=nombre,
        PasswordHash=password_hash,
        Apellido=apellido,
        gmail=gmail,
        Whatsapp=whatsapp,
        WppEntero=wpp_entero,
    )
    session.add(user)
    await session.flush()
    return _user_to_dict(user)


async def get_or_create_google_user(
    session: AsyncSession,
    gmail: str,
    nombre: str,
    apellido: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Find user by gmail or create a new one. Returns (user_dict, is_new)."""
    existing = await get_user_by_gmail(session, gmail)
    if existing:
        return existing, False

    user = User(
        Nombre=nombre,
        Apellido=apellido or "",
        gmail=gmail,
        PasswordHash=None,
    )
    session.add(user)
    await session.flush()
    return _user_to_dict(user), True


async def update_user_profile(
    session: AsyncSession,
    user_id: int,
    apellido: str | None = None,
    gmail: str | None = None,
    whatsapp: str | None = None,
    wpp_entero: str | None = None,
) -> bool:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return False

    if apellido is not None:
        user.Apellido = apellido
    if gmail is not None:
        user.gmail = gmail
    if whatsapp is not None:
        # Check WPP not taken by another user
        if wpp_entero:
            existing = await get_user_by_wpp(session, wpp_entero)
            if existing and existing["id"] != user_id:
                raise ValueError("Ese número de WhatsApp ya está vinculado a otra cuenta")
        user.Whatsapp = whatsapp
        user.WppEntero = wpp_entero

    await session.flush()
    return True


async def complete_onboarding(session: AsyncSession, user_id: int) -> bool:
    """Mark onboarding as completed for a user."""
    from datetime import datetime, UTC
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return False
    user.OnboardingCompletado = True
    user.OnboardingCompletadoAt = datetime.now(UTC)
    await session.flush()
    return True


def _user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "Id": user.id,
        "Nombre": user.Nombre,
        "Apellido": user.Apellido or "",
        "gmail": user.gmail or "",
        "WppEntero": user.WppEntero or "",
        "Whatsapp": user.Whatsapp or "",
        "PasswordHash": user.PasswordHash or "",
        "ID_Sheets": user.ID_Sheets or "",
        "OnboardingCompletado": bool(user.OnboardingCompletado),
    }
