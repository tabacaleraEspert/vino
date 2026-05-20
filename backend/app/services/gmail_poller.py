"""
Gmail poller — reads bank notification emails and creates movements.

Replaces the n8n Gmail trigger pipeline. Called by POST /gmail/poll
which is triggered by Azure Timer every 1-2 minutes.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, UTC
from html.parser import HTMLParser
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_token
from app.models.user import User
from app.services.bank_email_filters import matches_bank_filter, build_gmail_query
from app.services.email_expense_extractor import extract_expense_from_email
from app.services.pipeline_log import log_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text: list[str] = []

    def handle_data(self, data: str):
        self._text.append(data)

    def get_text(self) -> str:
        return " ".join(self._text)


def strip_html(html: str) -> str:
    """Strip HTML tags and return plain text."""
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


# ---------------------------------------------------------------------------
# Gmail API helpers (sync — called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _build_gmail_service(refresh_token: str):
    """Build a Gmail API service from a refresh token."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    return build("gmail", "v1", credentials=creds)


def _list_messages(service, query: str, max_results: int = 20) -> list[dict]:
    """List Gmail messages matching a query (sync)."""
    result = service.users().messages().list(
        userId="me", q=query, maxResults=max_results,
    ).execute()
    return result.get("messages", [])


def _get_message(service, msg_id: str) -> dict:
    """Get a single Gmail message with full content (sync)."""
    return service.users().messages().get(
        userId="me", id=msg_id, format="full",
    ).execute()


def _extract_email_parts(msg: dict) -> tuple[str, str, str]:
    """Extract sender, subject, and body text from a Gmail message."""
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    sender = headers.get("from", "")
    subject = headers.get("subject", "")

    # Extract body
    body = ""
    payload = msg.get("payload", {})

    def _get_body_from_parts(parts: list) -> str:
        for part in parts:
            mime = part.get("mimeType", "")
            if mime == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            elif mime == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    return strip_html(base64.urlsafe_b64decode(data).decode("utf-8", errors="replace"))
            elif "parts" in part:
                result = _get_body_from_parts(part["parts"])
                if result:
                    return result
        return ""

    if "parts" in payload:
        body = _get_body_from_parts(payload["parts"])
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            mime = payload.get("mimeType", "")
            body = strip_html(decoded) if "html" in mime else decoded

    return sender, subject, body


# ---------------------------------------------------------------------------
# Per-user polling
# ---------------------------------------------------------------------------

async def poll_user_gmail(
    db: AsyncSession,
    user_id: int,
    gmail: str,
    refresh_token_encrypted: str,
    last_message_id: str | None = None,
) -> dict[str, Any]:
    """
    Poll one user's Gmail for bank expense notifications.

    Returns: {"processed": N, "created": N, "duplicated": N, "errors": N}
    """
    refresh_token = decrypt_token(refresh_token_encrypted)

    try:
        service = await asyncio.to_thread(_build_gmail_service, refresh_token)
    except Exception as e:
        logger.error("Failed to build Gmail service for user %d: %s", user_id, e, exc_info=True)
        log_event("gmail_error", user_id=user_id, gmail=gmail, error=str(e), step="build_service")
        return {"user_id": user_id, "error": str(e)}

    # Build query — last 3 days of bank emails (resilient to downtime, dedup prevents duplicates)
    query = build_gmail_query(days_back=3)

    try:
        messages = await asyncio.to_thread(_list_messages, service, query, 30)
    except Exception as e:
        logger.error("Gmail list failed for user %d: %s", user_id, e, exc_info=True)
        return {"user_id": user_id, "error": str(e)}

    log_event("gmail_query", user_id=user_id, gmail=gmail, query=query, messages_found=len(messages) if messages else 0)

    if not messages:
        logger.info("Gmail poll user %d: no messages found for query: %s", user_id, query)
        return {"user_id": user_id, "processed": 0, "created": 0, "duplicated": 0, "errors": 0}

    logger.info("Gmail poll user %d: found %d messages", user_id, len(messages))

    stats = {"user_id": user_id, "processed": 0, "created": 0, "duplicated": 0, "errors": 0}

    # Collect all message IDs from this batch for set-based dedup
    # Gmail IDs are NOT sequential — lexicographic comparison doesn't work
    seen_ids: set[str] = set()
    if last_message_id:
        seen_ids.add(last_message_id)

    last_successfully_processed_id: str | None = None

    # Process oldest first for consistent tracking
    from app.api.v1.ingest import process_ingest

    for msg_ref in reversed(messages):
        msg_id = msg_ref["id"]

        # Skip already-processed messages (origin_id dedup in ingest handles the rest)
        if msg_id in seen_ids:
            continue
        seen_ids.add(msg_id)

        try:
            # Use savepoint so a failure doesn't corrupt the session for other messages
            async with db.begin_nested():
                msg = await asyncio.to_thread(_get_message, service, msg_id)
                sender, subject, body = _extract_email_parts(msg)

                # Double-check against bank filters
                matched = matches_bank_filter(sender, subject)
                log_event("email_found", user_id=user_id, gmail=gmail,
                          msg_id=msg_id, sender=sender[:80], subject=subject[:120],
                          matched_filter=matched)

                if not matched:
                    logger.debug("Gmail poll user %d: skipped non-bank email from=%s subject=%s", user_id, sender[:60], subject[:80])
                    last_successfully_processed_id = msg_id
                    continue

                logger.info("Gmail poll user %d: matched bank email from=%s subject=%s", user_id, sender[:60], subject[:80])

                stats["processed"] += 1

                # Extract expense data with GPT
                extracted = await extract_expense_from_email(subject, sender, body)
                log_event("extraction_result", user_id=user_id, gmail=gmail,
                          msg_id=msg_id, subject=subject[:120], extraction=extracted)

                if not extracted.get("datos_completos"):
                    logger.warning(
                        "Gmail poll user %d: extraction incomplete for msg %s subject=%s — %s",
                        user_id, msg_id, subject[:60], extracted.get("dato_faltante", "unknown"),
                    )
                    last_successfully_processed_id = msg_id
                    continue

                # Build ingest payload (same format as n8n sends)
                ingest_payload = {
                    "usuario_gmail": gmail,
                    "fecha": extracted.get("fecha"),
                    "tipo": extracted.get("tipo", "Gasto"),
                    "monto": extracted.get("monto", 0),
                    "moneda": extracted.get("moneda", "ARS"),
                    "comercio_raw": extracted.get("comercio_raw", ""),
                    "descripcion": extracted.get("descripcion", ""),
                    "medio_pago_raw": extracted.get("medio_de_pago", ""),
                    "from_email": sender,
                    "asunto": subject,
                    "origen": "Gmail",
                    "origen_id": f"gmail_{msg_id}",
                }

                result = await process_ingest(db, ingest_payload)
                status = result.get("status", "")
                regla = result.get("regla", {})
                log_event("ingest_result", user_id=user_id, gmail=gmail,
                          msg_id=msg_id, status=status,
                          monto=ingest_payload.get("monto"),
                          comercio=ingest_payload.get("comercio_raw", ""),
                          categoria=regla.get("categoria", ""),
                          subcategoria=regla.get("subcategoria", ""),
                          movimiento_id=result.get("movimiento", {}).get("id") or result.get("movimiento", {}).get("Id"))

                if status == "creado":
                    stats["created"] += 1
                    # Send WhatsApp notification for new movement
                    await _notify_whatsapp(result, ingest_payload)
                elif "duplicado" in status:
                    stats["duplicated"] += 1

            # Only mark as processed if the savepoint committed successfully
            last_successfully_processed_id = msg_id

        except Exception as e:
            logger.error("Error processing Gmail message %s for user %d: %s", msg_id, user_id, e, exc_info=True)
            log_event("pipeline_error", user_id=user_id, gmail=gmail,
                      msg_id=msg_id, error=str(e))
            stats["errors"] += 1
            # Savepoint was rolled back automatically — session is still usable

    # Update last polled timestamp always, but only advance message ID if something succeeded
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        user.GmailLastPolledAt = datetime.now(UTC)
        if last_successfully_processed_id:
            user.GmailLastMessageId = last_successfully_processed_id
        await db.flush()

    log_event("poll_summary", user_id=user_id, gmail=gmail,
              processed=stats["processed"], created=stats["created"],
              duplicated=stats["duplicated"], errors=stats["errors"])
    logger.info(
        "Gmail poll for user %d: processed=%d created=%d dup=%d errors=%d",
        user_id, stats["processed"], stats["created"], stats["duplicated"], stats["errors"],
    )
    return stats


# ---------------------------------------------------------------------------
# WhatsApp notification after Gmail ingest
# ---------------------------------------------------------------------------

_CATEGORY_EMOJI = {
    "alimentacion": "🍽️", "alimentos": "🍽️",
    "transporte": "🚗",
    "entretenimiento": "🎬",
    "salud": "💊",
    "ropa": "👕",
    "vivienda": "🏠", "servicios": "🏠",
    "educacion": "📚", "educación": "📚",
}


async def _notify_whatsapp(ingest_result: dict, payload: dict) -> None:
    """Send WhatsApp confirmation after a Gmail-ingested movement is created."""
    try:
        from app.services.twilio_client import send_whatsapp

        usuario = ingest_result.get("usuario", {})
        wpp_to = usuario.get("wpp_entero", "")
        if not wpp_to:
            return

        movimiento = ingest_result.get("movimiento", {})
        regla = ingest_result.get("regla", {})

        monto = payload.get("monto", 0)
        moneda = payload.get("moneda", "ARS")
        comercio_raw = payload.get("comercio_raw", "")
        descripcion = payload.get("descripcion", "")
        categoria = regla.get("categoria", "Otros")
        subcategoria = regla.get("subcategoria", "")

        emoji = _CATEGORY_EMOJI.get(categoria.lower(), "💸")
        monto_fmt = f"${monto:,.0f}".replace(",", ".")

        msg = f"{emoji} *{monto_fmt}*"
        if moneda != "ARS":
            msg += f" {moneda}"
        if comercio_raw:
            msg += f" en *{comercio_raw}*"
        elif descripcion:
            msg += f" — {descripcion}"

        msg += f"\n📂 {categoria}"
        if subcategoria and subcategoria != "Gastos no categorizados":
            msg += f" / {subcategoria}"

        msg += "\n✅ Registrado (Gmail)"

        mov_id = movimiento.get("id") or movimiento.get("Id")
        if mov_id:
            msg += f"\n\n_Mal categorizado? Respondé:_\n_CAMBIAR {mov_id} + categoría_"

        sent = await send_whatsapp(wpp_to, msg)
        log_event("whatsapp_sent", user_id=usuario.get("id"),
                  to=wpp_to, success=bool(sent),
                  comercio=comercio_raw, monto=monto)
    except Exception as e:
        # Non-blocking — don't fail the poll if notification fails
        logger.warning("WhatsApp notification failed: %s", e)
        log_event("whatsapp_sent", user_id=usuario.get("id"),
                  to=wpp_to if 'wpp_to' in dir() else "",
                  success=False, error=str(e))


# ---------------------------------------------------------------------------
# Poll all connected users
# ---------------------------------------------------------------------------

async def poll_all_users(db: AsyncSession) -> list[dict[str, Any]]:
    """Poll Gmail for all users with connected Gmail accounts."""
    stmt = select(User).where(User.GmailRefreshToken.isnot(None))
    result = await db.execute(stmt)
    users = result.scalars().all()

    if not users:
        return []

    results = []
    for user in users:
        try:
            r = await poll_user_gmail(
                db,
                user_id=user.id,
                gmail=user.gmail or "",
                refresh_token_encrypted=user.GmailRefreshToken,
                last_message_id=user.GmailLastMessageId,
            )
            results.append(r)
        except Exception as e:
            logger.error("Poll failed for user %d: %s", user.id, e)
            results.append({"user_id": user.id, "error": str(e)})

    return results
