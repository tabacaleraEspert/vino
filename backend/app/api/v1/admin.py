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


@router.get("/users")
async def list_users(
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with key stats. Admin only."""
    from sqlalchemy import select, func
    from app.models.user import User
    from app.models.movimiento_orm import Movimiento

    stmt = select(User).order_by(User.id)
    result = await db.execute(stmt)
    users = result.scalars().all()

    # Movimiento counts per user
    mov_stmt = (
        select(Movimiento.Id_usuario, func.count().label("total"))
        .group_by(Movimiento.Id_usuario)
    )
    mov_result = await db.execute(mov_stmt)
    mov_counts = {r.Id_usuario: r.total for r in mov_result.all()}

    return {
        "users": [
            {
                "id": u.id,
                "nombre": u.Nombre,
                "apellido": u.Apellido or "",
                "gmail": u.gmail or "",
                "whatsapp": u.Whatsapp or "",
                "wpp_vinculado": bool(u.WppEntero),
                "gmail_conectado": bool(u.GmailRefreshToken),
                "gmail_last_polled": u.GmailLastPolledAt.isoformat() if u.GmailLastPolledAt else None,
                "onboarding": u.OnboardingCompletado,
                "movimientos": mov_counts.get(u.id, 0),
                "created_at": u.CreatedAt.isoformat() if u.CreatedAt else None,
            }
            for u in users
        ]
    }
