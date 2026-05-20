"""In-memory ring buffer for pipeline event logging.

Stores the last ~200 events from the Gmail→GPT→Ingest pipeline.
Events are lost on restart — this is for real-time monitoring only.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, UTC
from typing import Any

_MAX_EVENTS = 200
_events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)


def log_event(
    event_type: str,
    *,
    user_id: int | None = None,
    gmail: str | None = None,
    **data: Any,
) -> None:
    """Append a pipeline event to the ring buffer."""
    _events.append({
        "ts": datetime.now(UTC).isoformat(),
        "event": event_type,
        "user_id": user_id,
        "gmail": gmail,
        **data,
    })


def get_events(
    *,
    user_id: int | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return events from the buffer, newest first, with optional filters."""
    out: list[dict[str, Any]] = []
    for ev in reversed(_events):
        if user_id is not None and ev.get("user_id") != user_id:
            continue
        if event_type is not None and ev.get("event") != event_type:
            continue
        out.append(ev)
        if len(out) >= limit:
            break
    return out
