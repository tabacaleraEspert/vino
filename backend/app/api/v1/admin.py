from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_master_key, create_access_token
from app.db.session import get_db
from app.repositories.user_repo import get_user_by_nombre

router = APIRouter()


class ImpersonateIn(BaseModel):
    username: str


@router.post("/impersonate", dependencies=[Depends(require_master_key)])
async def impersonate(payload: ImpersonateIn, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_nombre(db, payload.username.strip())
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    token = create_access_token(sub=str(user.get("id", payload.username)))
    return {"access_token": token, "token_type": "bearer"}
