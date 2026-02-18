from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_master_key, create_access_token
from app.db.users import get_user_by_nombre

router = APIRouter()


class ImpersonateIn(BaseModel):
    username: str


@router.post("/impersonate", dependencies=[Depends(require_master_key)])
def impersonate(payload: ImpersonateIn):
    user = get_user_by_nombre(payload.username.strip())
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    id_sheets = (user.get("ID_Sheets") or "").strip()
    token = create_access_token(
        sub=str(user.get("id", payload.username)),
        id_sheets=id_sheets or None,
    )
    return {"access_token": token, "token_type": "bearer"}
