import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import create_access_token, require_user, verify_password
from app.db.users import get_user_by_nombre

router = APIRouter()
logger = logging.getLogger(__name__)


class LoginIn(BaseModel):
    username: str  # Nombre del usuario
    password: str


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
    if not id_sheets:
        raise HTTPException(
            status_code=400,
            detail="Usuario sin ID_Sheets configurado. Contactar administrador.",
        )

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
