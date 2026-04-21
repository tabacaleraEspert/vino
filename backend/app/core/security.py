"""Authentication and security utilities."""
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
    expires_min: Optional[int] = None,
) -> str:
    """Create a JWT token with sub claim."""
    exp_minutes = expires_min or settings.JWT_EXPIRE_MIN
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    """FastAPI dependency: validates JWT and returns payload."""
    if not creds:
        raise HTTPException(status_code=401, detail="Falta Authorization Bearer")
    payload = decode_token(creds.credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token sin identificador de usuario")
    return payload


def hash_password(password: str) -> str:
    """Generate bcrypt hash for storage."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def require_master_key(
    x_master_key: Optional[str] = Header(default=None, alias="X-Master-Key"),
) -> None:
    """FastAPI dependency: requires valid master key header."""
    if not x_master_key or x_master_key != settings.MASTER_KEY:
        raise HTTPException(status_code=401, detail="Master Key inválida")
