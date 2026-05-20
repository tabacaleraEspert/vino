from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import require_master_key, require_admin, create_access_token
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


@router.get("/pipeline-log")
async def pipeline_log(
    admin_id: int = Depends(require_admin),
    user_id: Optional[int] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=200),
):
    """Return pipeline events from the in-memory ring buffer. Admin only."""
    from app.services.pipeline_log import get_events
    events = get_events(user_id=user_id, event_type=event_type, limit=limit)
    return {"events": events, "admin_user_ids": settings.ADMIN_USER_IDS}
