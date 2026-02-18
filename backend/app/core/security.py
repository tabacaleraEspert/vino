from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer = HTTPBearer(auto_error=False)


def create_access_token(
    sub: str,
    id_sheets: Optional[str] = None,
    expires_min: Optional[int] = None,
) -> str:
    exp_minutes = expires_min or settings.JWT_EXPIRE_MIN
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }
    if id_sheets:
        payload["id_sheets"] = id_sheets
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not creds:
        raise HTTPException(status_code=401, detail="Falta Authorization Bearer")
    payload = decode_token(creds.credentials)
    # Establecer spreadsheet_id en contexto para que Sheets use el del usuario
    id_sheets = payload.get("id_sheets")
    if id_sheets:
        from app.sheets.registry import set_current_spreadsheet_id
        set_current_spreadsheet_id(id_sheets)
    return payload


def hash_password(password: str) -> str:
    """Genera hash bcrypt para almacenar en BD."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica password contra hash bcrypt."""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def require_master_key(
    x_master_key: Optional[str] = Header(default=None, alias="X-Master-Key")
) -> None:
    if not x_master_key or x_master_key != settings.MASTER_KEY:
        raise HTTPException(status_code=401, detail="Master Key inválida")
