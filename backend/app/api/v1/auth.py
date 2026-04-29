import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, require_user, verify_password
from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.user_repo import (
    complete_onboarding,
    create_user,
    get_or_create_google_user,
    get_user_by_nombre,
    get_user_by_id,
    update_user_profile,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str
    password: str
    apellido: str | None = None
    email: str | None = None
    whatsapp: str | None = None  # e.g. "+5491112345678"


@router.post("/register")
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña son requeridos")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    # Normalize WhatsApp number
    wpp_raw = payload.whatsapp.strip() if payload.whatsapp else None
    wpp_entero = None
    if wpp_raw:
        # Remove spaces, dashes; ensure starts with +
        wpp_clean = wpp_raw.replace(" ", "").replace("-", "")
        if not wpp_clean.startswith("+"):
            wpp_clean = "+" + wpp_clean
        wpp_entero = f"whatsapp:{wpp_clean}"

    try:
        user = await create_user(
            db,
            nombre=payload.username.strip(),
            password_hash=hash_password(payload.password),
            apellido=payload.apellido.strip() if payload.apellido else None,
            gmail=payload.email.strip() if payload.email else None,
            whatsapp=wpp_clean if wpp_raw else None,
            wpp_entero=wpp_entero,
        )
        # Seed default categories for the new user
        from app.services.seed_categories import seed_default_categories
        try:
            await seed_default_categories(db, user["id"])
        except Exception as e:
            logger.warning("Failed to seed categories for user %s: %s", user.get("id"), e)

        logger.info("register_ok nombre=%s id=%s", user.get("Nombre"), user.get("id"))
        return {
            "message": "Usuario creado correctamente. Ya puedes iniciar sesión.",
            "user": {
                "id": user.get("id"),
                "nombre": user.get("Nombre", ""),
                "apellido": user.get("Apellido", ""),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class GoogleAuthIn(BaseModel):
    credential: str  # Google ID token from frontend


@router.post("/google")
async def google_auth(payload: GoogleAuthIn, db: AsyncSession = Depends(get_db)):
    """
    Authenticate via Google Sign-In.

    Verifies the Google ID token server-side, finds or creates the user,
    seeds default categories for new users, and returns a JWT.
    """
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth no configurado")

    # Verify Google ID token (sync call — run in threadpool)
    try:
        idinfo = await asyncio.to_thread(
            id_token.verify_oauth2_token,
            payload.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido")

    email = idinfo.get("email")
    if not email or not idinfo.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email no verificado por Google")

    nombre = idinfo.get("given_name") or email.split("@")[0]
    apellido = idinfo.get("family_name")

    user, is_new = await get_or_create_google_user(
        db, gmail=email, nombre=nombre, apellido=apellido,
    )

    if is_new:
        from app.services.seed_categories import seed_default_categories
        try:
            await seed_default_categories(db, user["id"])
        except Exception as e:
            logger.warning("Failed to seed categories for Google user %s: %s", user["id"], e)

    user_id = str(user["id"])
    logger.info("google_auth_%s gmail=%s id=%s", "new" if is_new else "existing", email, user_id)

    token = create_access_token(sub=user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "is_new_user": is_new,
        "onboarding_completado": user.get("OnboardingCompletado", False),
        "user": {
            "id": user_id,
            "nombre": user.get("Nombre", ""),
            "apellido": user.get("Apellido", ""),
            "gmail": user.get("gmail", ""),
        },
    }


@router.post("/login")
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="username/password requeridos")

    user = await get_user_by_nombre(db, payload.username.strip())
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    pwd_hash = user.get("PasswordHash") or ""
    if not verify_password(payload.password, pwd_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    user_id = user.get("id") or user.get("Id")
    if user_id is None or user_id == "":
        raise HTTPException(status_code=500, detail="Error interno: usuario sin ID")

    user_id = str(user_id)
    logger.info("login_ok nombre=%s id_usuario=%s", payload.username, user_id)
    token = create_access_token(sub=user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "onboarding_completado": user.get("OnboardingCompletado", False),
        "user": {
            "id": str(user.get("id") or user.get("Id") or ""),
            "nombre": user.get("Nombre", ""),
            "apellido": user.get("Apellido", ""),
            "gmail": user.get("gmail", ""),
            "whatsapp": user.get("Whatsapp", ""),
        },
    }


@router.get("/me")
async def me(user=Depends(require_user)):
    return {"user": user}


@router.patch("/onboarding")
async def mark_onboarding_complete(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark onboarding as completed for the authenticated user."""
    ok = await complete_onboarding(db, id_usuario)
    if not ok:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"onboarding_completado": True}


class ProfileUpdate(BaseModel):
    apellido: str | None = None
    email: str | None = None
    whatsapp: str | None = None


@router.get("/profile")
async def get_profile(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get full user profile."""
    user = await get_user_by_id(db, id_usuario)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "id": user["id"],
        "nombre": user["Nombre"],
        "apellido": user["Apellido"],
        "email": user["gmail"],
        "whatsapp": user["Whatsapp"],
        "whatsapp_vinculado": bool(user["WppEntero"]),
    }


@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdate,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile (apellido, email, whatsapp)."""
    wpp_clean = None
    wpp_entero = None
    if payload.whatsapp is not None:
        wpp_raw = payload.whatsapp.strip()
        if wpp_raw:
            wpp_clean = wpp_raw.replace(" ", "").replace("-", "")
            if not wpp_clean.startswith("+"):
                wpp_clean = "+" + wpp_clean
            wpp_entero = f"whatsapp:{wpp_clean}"
        else:
            # Empty string = unlink
            wpp_clean = ""
            wpp_entero = ""

    updated = await update_user_profile(
        db, id_usuario,
        apellido=payload.apellido,
        gmail=payload.email,
        whatsapp=wpp_clean,
        wpp_entero=wpp_entero,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "message": "Perfil actualizado",
        "whatsapp_vinculado": bool(wpp_entero),
    }
