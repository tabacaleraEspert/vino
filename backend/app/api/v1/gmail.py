"""Gmail integration endpoints — connect, disconnect, status, and poll."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import encrypt_token, decrypt_token
from app.core.security import require_master_key
from app.db.session import get_db
from app.deps import get_current_user_id
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Connect — exchange auth code for refresh token
# ---------------------------------------------------------------------------

class GmailConnectIn(BaseModel):
    code: str  # Authorization code from frontend


@router.post("/connect")
async def gmail_connect(
    payload: GmailConnectIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a Google OAuth authorization code for a refresh token.

    The frontend triggers this after the user consents to gmail.readonly scope
    using useGoogleLogin({ flow: 'auth-code', scope: 'gmail.readonly' }).
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth no configurado")

    # Exchange auth code for tokens
    try:
        import httpx
        token_resp = await asyncio.to_thread(
            _exchange_auth_code, payload.code,
        )
    except Exception as e:
        logger.error("Gmail token exchange failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Error al conectar Gmail: {e}")

    refresh_token = token_resp.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="No se recibió refresh_token. Probá desvinculando la app en tu cuenta de Google y volvé a conectar.",
        )

    # Store encrypted refresh token
    stmt = select(User).where(User.id == id_usuario)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.GmailRefreshToken = encrypt_token(refresh_token)
    user.GmailConnectedAt = datetime.now(UTC)
    await db.flush()

    logger.info("Gmail connected for user %d", id_usuario)
    return {"status": "connected"}


def _exchange_auth_code(code: str) -> dict:
    """Exchange authorization code for tokens (sync — called via to_thread)."""
    import httpx
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": "postmessage",  # For popup-based flow
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise ValueError(f"Google token endpoint returned {resp.status_code}: {resp.text[:200]}")
    return resp.json()


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------

@router.delete("/connect")
async def gmail_disconnect(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect Gmail — clear stored tokens."""
    stmt = select(User).where(User.id == id_usuario)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.GmailRefreshToken = None
    user.GmailConnectedAt = None
    user.GmailLastPolledAt = None
    user.GmailLastMessageId = None
    await db.flush()

    logger.info("Gmail disconnected for user %d", id_usuario)
    return {"status": "disconnected"}


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status")
async def gmail_status(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Check if Gmail is connected for the authenticated user."""
    stmt = select(User).where(User.id == id_usuario)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    connected = bool(user.GmailRefreshToken)
    return {
        "connected": connected,
        "connected_at": user.GmailConnectedAt.isoformat() if user.GmailConnectedAt else None,
        "last_polled_at": user.GmailLastPolledAt.isoformat() if user.GmailLastPolledAt else None,
    }


# ---------------------------------------------------------------------------
# Poll — triggered by Azure Timer or manual cron
# ---------------------------------------------------------------------------

@router.post("/poll")
async def trigger_gmail_poll(
    _: None = Depends(require_master_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Poll Gmail for all connected users. Protected by master key.
    Called by Azure Timer Trigger every 1-2 minutes.
    """
    from app.services.gmail_poller import poll_all_users
    results = await poll_all_users(db)
    return {"results": results}
