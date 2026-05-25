"""Async repository for Users."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def _next_user_id(session: AsyncSession) -> int:
    """Generate next user ID (table has no IDENTITY)."""
    result = await session.execute(select(func.coalesce(func.max(User.id), 0)))
    return result.scalar_one() + 1


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

    next_id = await _next_user_id(session)
    user = User(
        id=next_id,
        Nombre=nombre,
        PasswordHash=password_hash,
        Apellido=apellido or "",
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

    next_id = await _next_user_id(session)
    user = User(
        id=next_id,
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
    nombre: str | None = None,
    apellido: str | None = None,
    apodo: str | None = None,
    gmail: str | None = None,
    whatsapp: str | None = None,
    wpp_entero: str | None = None,
) -> bool:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return False

    if nombre is not None:
        user.Nombre = nombre
    if apellido is not None:
        user.Apellido = apellido
    if apodo is not None:
        user.Apodo = apodo
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


async def save_wpp_otp(
    session: AsyncSession,
    user_id: int,
    code: str,
    phone: str,
    expires_at: datetime,
) -> bool:
    """Save a WhatsApp OTP code for verification."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return False
    user.WppOtpCode = code
    user.WppOtpPhone = phone
    user.WppOtpExpiresAt = expires_at
    await session.flush()
    return True


async def verify_and_link_wpp(
    session: AsyncSession,
    user_id: int,
    code: str,
    phone: str,
) -> dict[str, Any] | None:
    """
    Verify OTP code and link WhatsApp number if correct.
    Returns None on failure, user dict on success.
    """
    from datetime import datetime, UTC

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None

    # Validate OTP
    if not user.WppOtpCode or not user.WppOtpExpiresAt or not user.WppOtpPhone:
        return None
    if user.WppOtpCode != code:
        return None
    if user.WppOtpPhone != phone:
        return None
    # Timezone-safe expiration check
    expires = user.WppOtpExpiresAt
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if datetime.now(UTC) > expires:
        return None

    # Check uniqueness
    wpp_entero = f"whatsapp:{phone}"
    existing = await get_user_by_wpp(session, wpp_entero)
    if existing and existing["id"] != user_id:
        raise ValueError("Ese número de WhatsApp ya está vinculado a otra cuenta")

    # Link and clear OTP
    user.Whatsapp = phone
    user.WppEntero = wpp_entero
    user.WppOtpCode = None
    user.WppOtpExpiresAt = None
    user.WppOtpPhone = None
    await session.flush()
    return _user_to_dict(user)


def _user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "Id": user.id,
        "Nombre": user.Nombre,
        "Apellido": user.Apellido or "",
        "Apodo": user.Apodo or "",
        "gmail": user.gmail or "",
        "WppEntero": user.WppEntero or "",
        "Whatsapp": user.Whatsapp or "",
        "PasswordHash": user.PasswordHash or "",
        "ID_Sheets": user.ID_Sheets or "",
        "OnboardingCompletado": bool(user.OnboardingCompletado),
        "OnboardingStep": user.OnboardingStep or 0,
    }
