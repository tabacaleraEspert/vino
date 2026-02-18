"""
Dependencias compartidas para API.
Setea spreadsheet_id en el thread actual (contextvars no propagan al thread pool de FastAPI).
"""

from app.sheets.registry import set_current_spreadsheet_id


def set_sheets_context(user: dict) -> None:
    """Setea spreadsheet_id en el thread actual para que SHEETS use el del usuario."""
    if user.get("id_sheets"):
        set_current_spreadsheet_id(user["id_sheets"])
