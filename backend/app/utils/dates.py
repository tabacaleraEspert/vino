"""Date utilities — Argentina timezone helpers."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# Argentina Time (UTC-3), no DST
ART = timezone(timedelta(hours=-3))


def today_ar() -> date:
    """Return today's date in Argentina timezone."""
    return datetime.now(ART).date()
