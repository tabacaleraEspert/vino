"""
Inactivity reminder — nudge users who haven't logged expenses in 2+ days.

Called by a scheduled endpoint (Azure Timer or cron). Sends a WhatsApp
message using a pre-approved template with a random fun message.
"""
from __future__ import annotations

import logging
import random
from datetime import timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.movimiento_orm import Movimiento
from app.models.user import User
from app.services.twilio_client import send_whatsapp
from app.utils.dates import today_ar

logger = logging.getLogger(__name__)

# Pool of fun reminder messages — rotated randomly.
# The template starts with "Hola!!" hardcoded, so these flow after it.
_REMINDER_MESSAGES = [
    "Hace 2 dias que no registras gastos... o estas ahorrando como campeon o se te olvido contarnos.",
    "Tu billetera pregunta por vos. Dice que la extraña.",
    "Dato curioso: el 73% de la gente que deja de anotar gastos termina preguntandose a donde fue la plata.",
    "No registraste gastos hace rato. Esperamos que sea porque no gastaste y no porque te olvidaste.",
    "Tus finanzas te mandan saludos. Dicen que las tenes medio abandonadas.",
    "Si no gastas, genial. Si gastas y no anotas... ahi esta el problema.",
    "Anotar un gasto tarda 5 segundos. Arrepentirse de no haberlo anotado, mucho mas.",
    "Che, todo bien? Tu cuenta esta mas silenciosa que grupo de WhatsApp de familia un lunes.",
    "Llevas 2 dias sin anotar. Tu yo del futuro te va a agradecer si retomas.",
    "Anotar gastos es como ir al gym: cuesta empezar pero despues te sentis bien.",
    "Se detectaron 0 gastos registrados ultimamente. O sos millonario o se te paso.",
    "Tu presupuesto esta esperando noticias tuyas. No lo dejes en visto.",
    "Sabias que la gente que anota sus gastos ahorra en promedio un 20% mas? Solo digo.",
    "Paso a recordarte que existo. Con cariño, tu app de finanzas.",
    "2 dias sin gastos registrados. Es un record o un olvido?",
]


async def send_inactivity_reminders(db: AsyncSession) -> dict[str, Any]:
    """
    Find users inactive for 2+ days and send them a reminder via WhatsApp.

    Returns stats: {checked, reminded, skipped, errors}
    """
    template_sid = settings.TWILIO_REMINDER_CONTENT_SID
    if not template_sid:
        logger.warning("TWILIO_REMINDER_CONTENT_SID not configured, skipping reminders")
        return {"checked": 0, "reminded": 0, "skipped": 0, "errors": 0}

    today = today_ar()
    cutoff = today - timedelta(days=2)

    # Find users with WhatsApp connected
    stmt = select(User).where(and_(
        User.WppEntero.isnot(None),
        User.WppEntero != "",
    ))
    result = await db.execute(stmt)
    users = result.scalars().all()

    stats = {"checked": len(users), "reminded": 0, "skipped": 0, "errors": 0}

    for user in users:
        try:
            # Check last expense date for this user
            last_expense_stmt = select(func.max(Movimiento.Fecha)).where(and_(
                Movimiento.Id_usuario == user.id,
                Movimiento.TipoMovimiento == "Gasto",
            ))
            last_result = await db.execute(last_expense_stmt)
            last_date = last_result.scalar_one_or_none()

            if last_date and last_date >= cutoff:
                stats["skipped"] += 1
                continue

            # Pick a random message
            message = random.choice(_REMINDER_MESSAGES)

            sent = await send_whatsapp(
                user.WppEntero,
                content_sid=template_sid,
                content_variables={"1": message},
            )

            if sent:
                stats["reminded"] += 1
                logger.info("Reminder sent to user %d (%s)", user.id, user.Nombre)
            else:
                stats["errors"] += 1

        except Exception as e:
            logger.error("Reminder failed for user %d: %s", user.id, e)
            stats["errors"] += 1

    logger.info("Inactivity reminders: %s", stats)
    return stats
