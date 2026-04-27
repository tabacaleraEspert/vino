import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, require_user, verify_password
from app.db.session import get_db
from app.repositories.user_repo import create_user, get_user_by_nombre

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


@router.post("/register")
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña son requeridos")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    try:
        user = await create_user(
            db,
            nombre=payload.username.strip(),
            password_hash=hash_password(payload.password),
            apellido=payload.apellido.strip() if payload.apellido else None,
            gmail=payload.email.strip() if payload.email else None,
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
        "user": {
            "id": str(user.get("id") or user.get("Id") or ""),
            "nombre": user.get("Nombre", ""),
            "apellido": user.get("Apellido", ""),
            "gmail": user.get("gmail", ""),
        },
    }


@router.get("/me")
async def me(user=Depends(require_user)):
    return {"user": user}
