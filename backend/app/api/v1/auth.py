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
    save_wpp_otp,
    update_user_profile,
    verify_and_link_wpp,
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

    # Verify Google ID token — accept both web and iOS client IDs
    allowed_client_ids = [settings.GOOGLE_CLIENT_ID]
    if settings.GOOGLE_IOS_CLIENT_ID:
        allowed_client_ids.append(settings.GOOGLE_IOS_CLIENT_ID)

    idinfo = None
    for cid in allowed_client_ids:
        try:
            idinfo = await asyncio.to_thread(
                id_token.verify_oauth2_token,
                payload.credential,
                google_requests.Request(),
                cid,
            )
            break
        except ValueError:
            continue
    if idinfo is None:
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
        "onboarding_step": user.get("OnboardingStep", 0),
        "user": {
            "id": user_id,
            "nombre": user.get("Nombre", ""),
            "apellido": user.get("Apellido", ""),
            "gmail": user.get("gmail", ""),
        },
    }


class AppleAuthIn(BaseModel):
    id_token: str
    given_name: str | None = None
    family_name: str | None = None


@router.post("/apple")
async def apple_auth(payload: AppleAuthIn, db: AsyncSession = Depends(get_db)):
    """
    Authenticate via Sign in with Apple.

    Verifies the Apple ID token using Apple's public keys,
    finds or creates the user, and returns a JWT.
    """
    import jwt
    import httpx

    # Fetch Apple's public keys
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://appleid.apple.com/auth/keys")
            apple_keys = resp.json()
    except Exception:
        raise HTTPException(status_code=500, detail="No se pudo verificar con Apple")

    # Decode and verify the token
    try:
        header = jwt.get_unverified_header(payload.id_token)
        # Find the matching key
        key = None
        for k in apple_keys["keys"]:
            if k["kid"] == header["kid"]:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                break
        if key is None:
            raise ValueError("Key not found")

        idinfo = jwt.decode(
            payload.id_token,
            key,
            algorithms=["RS256"],
            audience="com.vino.finanzas",
            issuer="https://appleid.apple.com",
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Token de Apple invalido")

    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Email no disponible de Apple")

    nombre = payload.given_name or email.split("@")[0]
    apellido = payload.family_name

    user, is_new = await get_or_create_google_user(
        db, gmail=email, nombre=nombre, apellido=apellido,
    )

    if is_new:
        from app.services.seed_categories import seed_default_categories
        try:
            await seed_default_categories(db, user["id"])
        except Exception as e:
            logger.warning("Failed to seed categories for Apple user %s: %s", user["id"], e)

    user_id = str(user["id"])
    logger.info("apple_auth_%s email=%s id=%s", "new" if is_new else "existing", email, user_id)

    token = create_access_token(sub=user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "is_new_user": is_new,
        "onboarding_completado": user.get("OnboardingCompletado", False),
        "onboarding_step": user.get("OnboardingStep", 0),
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
        "onboarding_step": user.get("OnboardingStep", 0),
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


class OnboardingStepIn(BaseModel):
    step: int


@router.get("/onboarding/step")
async def get_onboarding_step(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's current onboarding step."""
    user = await get_user_by_id(db, id_usuario)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"step": user.get("OnboardingStep", 0)}


@router.patch("/onboarding/step")
async def set_onboarding_step(
    payload: OnboardingStepIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Save the user's current onboarding step."""
    from sqlalchemy import select
    from app.models.user import User
    stmt = select(User).where(User.id == id_usuario)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.OnboardingStep = payload.step
    await db.flush()
    return {"step": payload.step}


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


# ---------------------------------------------------------------------------
# WhatsApp OTP verification
# ---------------------------------------------------------------------------

class WhatsAppSendCode(BaseModel):
    whatsapp: str


class WhatsAppVerifyCode(BaseModel):
    whatsapp: str
    code: str


def _normalize_wpp(raw: str) -> str:
    """Normalize a WhatsApp number to +country format."""
    cleaned = raw.strip().replace(" ", "").replace("-", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


@router.post("/whatsapp/send-code")
async def whatsapp_send_code(
    payload: WhatsAppSendCode,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Send a 6-digit verification code to a WhatsApp number."""
    import secrets
    from datetime import datetime, timedelta, UTC

    phone = _normalize_wpp(payload.whatsapp)
    # Validate Argentina phone format: +54 + 10-11 digits
    digits_only = phone.lstrip("+")
    if len(digits_only) < 12 or not digits_only.isdigit():
        raise HTTPException(status_code=400, detail="Número de WhatsApp inválido. Debe tener formato +54XXXXXXXXXX")

    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = datetime.now(UTC) + timedelta(minutes=5)

    saved = await save_wpp_otp(db, id_usuario, code, phone, expires_at)
    if not saved:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Send code via WhatsApp — use template if configured, freeform as fallback
    from app.services.twilio_client import send_whatsapp

    wpp_to = f"whatsapp:{phone}"
    otp_template = settings.TWILIO_OTP_CONTENT_SID
    if otp_template:
        sent = await send_whatsapp(
            wpp_to,
            content_sid=otp_template,
            content_variables={"1": code},
        )
    else:
        sent = await send_whatsapp(
            wpp_to,
            f"Tu codigo de verificacion de *Fina* es: *{code}*\n\nExpira en 5 minutos.",
        )
    if not sent:
        raise HTTPException(status_code=502, detail="No se pudo enviar el mensaje de WhatsApp")

    await db.commit()
    return {"message": "Codigo enviado", "expires_in": 300}


@router.post("/whatsapp/verify-code")
async def whatsapp_verify_code(
    payload: WhatsAppVerifyCode,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Verify a WhatsApp OTP code and link the number to the user."""
    phone = _normalize_wpp(payload.whatsapp)
    code = payload.code.strip()

    if len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="El codigo debe ser de 6 digitos")

    try:
        result = await verify_and_link_wpp(db, id_usuario, code, phone)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not result:
        raise HTTPException(status_code=400, detail="Codigo incorrecto o expirado")

    await db.commit()
    return {"message": "WhatsApp verificado", "whatsapp_vinculado": True}
