"""
Endpoint bootstrap: devuelve múltiples catálogos en una sola llamada.
Reduce 5 requests del frontend a 1.
Categorías, subcategorías, presupuestos y reglas desde SQL; comercios desde store.
"""
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_user
from app.db.catalog import _get_id_usuario, list_categorias_sql, list_subcategorias_sql
from app.db.presupuestos import list_presupuestos_sql
from app.db.regla_comercio import list_reglas_comercio
from app.storage.store import get_all

router = APIRouter()


def _regla_to_raw(r: dict) -> dict:
    """Formato ReglaRaw para frontend."""
    return {
        "id": r["id"],
        "comercio": r.get("comercio", r.get("patron", "")),
        "categoria_id": r["categoria_id"],
        "categoria_nombre": r["categoria_nombre"],
        "subcategoria_id": r["subcategoria_id"],
        "subcategoria_nombre": r["subcategoria_nombre"],
        "timestamp": r.get("timestamp") or r.get("actualizadoEn"),
    }


@router.get("")
def bootstrap(user: dict = Depends(require_user)):
    """
    Devuelve categorias, subcategorias, reglas, presupuestos y comercios en una sola llamada.
    Categorías, subcategorías, presupuestos y reglas desde SQL; comercios desde store.
    """
    sid = user.get("id_sheets")
    if not sid:
        raise HTTPException(status_code=400, detail="Usuario sin ID_Sheets configurado")

    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Categorías y subcategorías desde SQL (no requieren spreadsheet context)
    def _categorias():
        rows = list_categorias_sql(id_usuario)
        return [{"id": r["id"], "nombre": r["nombre"], "icon": r["icon"], "color": r["color"]} for r in rows]

    def _subcategorias():
        rows = list_subcategorias_sql(id_usuario)
        return [{"id": r["id"], "categoria_id": r["categoria_id"], "nombre": r["nombre"]} for r in rows]

    def _reglas():
        rows = list_reglas_comercio(id_usuario)
        return [_regla_to_raw(r) for r in rows]

    def _presupuestos():
        rows = list_presupuestos_sql(id_usuario, periodo_mes=None)
        return [
            {
                "id": r["id"],
                "mes_anio": r.get("mes_anio", r.get("mesAño", "")),
                "categoria_id": r.get("categoria_id", ""),
                "categoria_nombre": r.get("categoria_nombre", ""),
                "subcategoria_id": r.get("subcategoria_id", ""),
                "subcategoria_nombre": r.get("subcategoria_nombre", ""),
                "monto": r.get("monto", str(r.get("Monto", 0))),
            }
            for r in rows
        ]

    def _comercios():
        return get_all("merchants")

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
