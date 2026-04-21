"""
Shared FastAPI dependencies.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_user
from app.db.session import get_db


async def get_current_user_id(user: dict = Depends(require_user)) -> int:
    """Extracts and validates user ID from JWT token."""
    sub = user.get("sub") or user.get("id")
    if sub is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Token sin identificador de usuario")
    try:
        return int(sub)
    except (TypeError, ValueError):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Identificador de usuario inválido")
