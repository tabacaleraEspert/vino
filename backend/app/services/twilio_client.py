"""Twilio WhatsApp client — send messages via Twilio REST API."""
from __future__ import annotations

import logging
from base64 import b64encode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_whatsapp(to: str, body: str) -> bool:
    """
    Send a WhatsApp message via Twilio API.

    Args:
        to: Recipient in format "whatsapp:+5491112345678"
        body: Message text (supports WhatsApp markdown: *bold*, _italic_)

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

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                data={
                    "From": settings.TWILIO_WHATSAPP_FROM,
                    "To": to,
                    "Body": body,
                },
                headers={"Authorization": f"Basic {auth}"},
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info("WhatsApp sent to %s (%d chars)", to, len(body))
                return True
            else:
                logger.error("Twilio error %d: %s", resp.status_code, resp.text[:200])
                return False
    except Exception as e:
        logger.error("Failed to send WhatsApp to %s: %s", to, e)
        return False
