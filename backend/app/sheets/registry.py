from contextvars import ContextVar
from typing import Dict

from pydantic import BaseModel

from app.core.config import settings

# Context var: spreadsheet_id del usuario autenticado (columna ID_Sheets de MaestroUsuarios)
_current_spreadsheet_id: ContextVar[str | None] = ContextVar(
    "spreadsheet_id", default=None
)


class SheetConfig(BaseModel):
    spreadsheet_id: str
    worksheet: str
    id_column: str = "Id"
    header_row: int = 1


def _build_sheets(spreadsheet_id: str) -> Dict[str, SheetConfig]:
    return {
        "movimientos": SheetConfig(
            spreadsheet_id=spreadsheet_id,
            worksheet="Movimientos de Gastos Personales",
            id_column="Id",
            header_row=1,
        ),
        "reglas": SheetConfig(
            spreadsheet_id=spreadsheet_id,
            worksheet="Reglas",
            id_column="Id",
            header_row=1,
        ),
        "categorias": SheetConfig(
            spreadsheet_id=spreadsheet_id,
            worksheet="Categoria",
            id_column="Id",
            header_row=1,
        ),
        "subcategorias": SheetConfig(
            spreadsheet_id=spreadsheet_id,
            worksheet="Sub-Categoria",
            id_column="Id",
            header_row=1,
        ),
        "presupuestos": SheetConfig(
            spreadsheet_id=spreadsheet_id,
            worksheet="Presupuesto",
            id_column="Id",
            header_row=1,
        ),
    }


def set_current_spreadsheet_id(sid: str | None) -> None:
    """Establece el ID de Sheets del usuario actual (por request)."""
    _current_spreadsheet_id.set(sid)


def get_current_spreadsheet_id() -> str:
    """
    Obtiene el spreadsheet_id del contexto (ID_Sheets del usuario en Azure).
    Se setea en require_user al decodificar el JWT.
    Fallback: SPREADSHEET_ID en .env (solo scripts/dev).
    """
    sid = _current_spreadsheet_id.get()
    if sid:
        return sid
    if settings.SPREADSHEET_ID:
        return settings.SPREADSHEET_ID
    raise RuntimeError(
        "No hay spreadsheet_id en contexto. Las rutas con Sheets requieren login; "
        "el ID viene de ID_Sheets en MaestroUsuarios. Para scripts: SPREADSHEET_ID en .env"
    )


class _SheetsProxy:
    """Proxy que devuelve SheetConfig usando el spreadsheet_id del contexto."""

    def __getitem__(self, key: str) -> SheetConfig:
        sid = get_current_spreadsheet_id()
        configs = _build_sheets(sid)
        if key not in configs:
            raise KeyError(key)
        return configs[key]


# Compatible con SHEETS["movimientos"] etc.
SHEETS: _SheetsProxy = _SheetsProxy()
