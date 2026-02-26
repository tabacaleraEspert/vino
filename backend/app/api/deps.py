"""
Dependencias compartidas para API.
Setea spreadsheet_id en el thread actual (contextvars no propagan al thread pool de FastAPI).
"""

from app.sheets.registry import set_current_spreadsheet_id


def set_sheets_context(user: dict) -> None:
    """Setea spreadsheet_id en el thread actual para que SHEETS use el del usuario."""
    sid = user.get("id_sheets")
    if sid and sid != "sql-only":
        set_current_spreadsheet_id(sid)
