"""
Endpoint bootstrap: devuelve múltiples catálogos en una sola llamada.
Reduce 5 requests del frontend a 1.
"""
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_user
from app.sheets.catalog_service import (
    list_categorias,
    list_subcategorias,
    list_reglas,
    list_presupuestos,
)
from app.sheets.registry import set_current_spreadsheet_id
from app.storage.store import get_all

router = APIRouter()


def _run_with_sheets(sid: str, fn):
    """Ejecuta fn en el thread actual con spreadsheet_id seteado (ContextVar no se propaga a threads)."""
    set_current_spreadsheet_id(sid)
    return fn()


@router.get("")
def bootstrap(user: dict = Depends(require_user)):
    """
    Devuelve categorias, subcategorias, reglas, presupuestos y comercios en una sola llamada.
    Requiere autenticación. Usa cache de Sheets cuando está caliente.
    """
    sid = user.get("id_sheets")
    if not sid:
        raise HTTPException(status_code=400, detail="Usuario sin ID_Sheets configurado")

    # Cada worker thread debe setear spreadsheet_id (ContextVar no se propaga a threads)
    def _categorias():
        return _run_with_sheets(sid, list_categorias)

    def _subcategorias():
        return _run_with_sheets(sid, list_subcategorias)

    def _reglas():
        return _run_with_sheets(sid, list_reglas)

    def _presupuestos():
        return _run_with_sheets(sid, list_presupuestos)

    def _comercios():
        return get_all("merchants")  # Store no usa spreadsheet_id

    # Refresco en paralelo si cache está frío (cada tabla tiene su lock)
    with ThreadPoolExecutor(max_workers=5) as ex:
        fut_cat = ex.submit(_categorias)
        fut_sub = ex.submit(_subcategorias)
        fut_reg = ex.submit(_reglas)
        fut_pre = ex.submit(_presupuestos)
        fut_com = ex.submit(_comercios)

        categorias = fut_cat.result()
        subcategorias = fut_sub.result()
        reglas = fut_reg.result()
        presupuestos = fut_pre.result()
        comercios = fut_com.result()

    return {
        "categorias": categorias,
        "subcategorias": subcategorias,
        "reglas": reglas,
        "presupuestos": presupuestos,
        "comercios": comercios,
    }
