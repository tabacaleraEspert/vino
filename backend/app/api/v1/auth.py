import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import create_access_token, hash_password, require_user, verify_password
from app.db.users import create_user as db_create_user, get_user_by_nombre

router = APIRouter()
logger = logging.getLogger(__name__)


class LoginIn(BaseModel):
    username: str  # Nombre del usuario
    password: str


class RegisterIn(BaseModel):
    username: str  # Nombre del usuario
    password: str
    apellido: str | None = None
    email: str | None = None


@router.post("/register")
def register(payload: RegisterIn):
    """Crea nuevo usuario. ID_Sheets queda vacío (modo SQL-only)."""
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña son requeridos")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    try:
        user = db_create_user(
            nombre=payload.username.strip(),
            password_hash=hash_password(payload.password),
            apellido=payload.apellido.strip() if payload.apellido else None,
            gmail=payload.email.strip() if payload.email else None,
        )
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
    except RuntimeError as e:
        if "SQL" in str(e) or "variables" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Servicio no configurado. Contactar administrador.",
            ) from e
        raise


@router.post("/login")
def login(payload: LoginIn):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="username/password requeridos")

    try:
        user = get_user_by_nombre(payload.username.strip())
    except RuntimeError as e:
        if "SQL" in str(e) or "variables" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Servicio de autenticación no configurado. Contactar administrador.",
            ) from e
        raise
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    pwd_hash = user.get("PasswordHash") or ""
    if not verify_password(payload.password, pwd_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    id_sheets = (user.get("ID_Sheets") or "").strip()
    # Permitir login sin ID_Sheets (usuarios SQL-only, creados por registro)
    if not id_sheets:
        id_sheets = "sql-only"

    # sub = id de MaestroUsuarios (usado para filtrar movimientos por Id_usuario)
    user_id = user.get("id") or user.get("Id")  # SQL Server puede devolver "Id"
    if user_id is None or user_id == "":
        logger.warning("login_user_id_missing nombre=%s user_keys=%s", payload.username, list(user.keys()))
        user_id = payload.username  # fallback (causará error en _get_id_usuario si no es numérico)
    else:
        user_id = str(user_id)
    logger.info("login_ok nombre=%s id_usuario=%s", payload.username, user_id)
    token = create_access_token(
        sub=user_id,
        id_sheets=id_sheets,
    )
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
def me(user=Depends(require_user)):
    return {"user": user}
