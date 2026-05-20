"""Twilio WhatsApp client — send messages via Twilio REST API."""
from __future__ import annotations

import logging
from base64 import b64encode

import httpx

from app.core.config import settings
from app.services.pipeline_log import log_event

logger = logging.getLogger(__name__)


async def send_whatsapp(
    to: str,
    body: str | None = None,
    *,
    content_sid: str | None = None,
    content_variables: dict | None = None,
) -> bool:
    """
    Send a WhatsApp message via Twilio API.

    Args:
        to: Recipient in format "whatsapp:+5491112345678"
        body: Message text (freeform — only works within 24h session window)
        content_sid: Twilio Content Template SID (for pre-approved templates)
        content_variables: Template variable values, e.g. {"1": "123456"}

    Returns:
        True if sent successfully, False on error.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.error("Twilio credentials not configured")
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"

    auth = b64encode(
        f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()
    ).decode()

    import json

    data: dict[str, str] = {
        "From": settings.TWILIO_WHATSAPP_FROM,
        "To": to,
    }
    if content_sid:
        data["ContentSid"] = content_sid
        if content_variables:
            data["ContentVariables"] = json.dumps(content_variables)
    elif body:
        data["Body"] = body
    else:
        logger.error("send_whatsapp: must provide body or content_sid")
        return False

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                data=data,
                headers={"Authorization": f"Basic {auth}"},
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info("WhatsApp sent to %s (template=%s)", to, content_sid or "freeform")
                log_event("wpp_outgoing", to=to, success=True,
                          template=content_sid or "freeform",
                          body_preview=(body or "")[:120])
                return True
            else:
                logger.error("Twilio error %d: %s", resp.status_code, resp.text[:200])
                log_event("wpp_outgoing", to=to, success=False,
                          template=content_sid or "freeform",
                          error=resp.text[:200])
                return False
    except Exception as e:
        logger.error("Failed to send WhatsApp to %s: %s", to, e)
        log_event("wpp_outgoing", to=to, success=False, error=str(e))
        return False
