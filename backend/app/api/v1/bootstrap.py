"""
Endpoint bootstrap: devuelve múltiples catálogos en una sola llamada.
Reduce 5 requests del frontend a 1.
Categorías, subcategorías, presupuestos y reglas desde SQL; comercios desde store.
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException

from app.cache.sql_catalog_cache import get_cached
from app.core.config import settings
from app.core.security import require_user
from app.db.catalog import _get_id_usuario, list_categorias_sql, list_subcategorias_sql
from app.db.comercios import list_comercios_sql
from app.utils.normalize import normalize_text
from app.db.movimientos import list_comercios_from_movimientos
from app.db.presupuestos import list_presupuestos_sql
from app.db.regla_comercio import list_reglas_comercio

logger = logging.getLogger(__name__)
router = APIRouter()
TTL = getattr(settings, "SQL_CATALOG_CACHE_TTL_SEC", 300)


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

    logger.info("bootstrap start id_usuario=%s sub=%s", id_usuario, user.get("sub"))

    # Catálogos con cache opcional (TTL 5 min por defecto)
    def _categorias():
        rows = get_cached(
            id_usuario, "categorias",
            lambda: list_categorias_sql(id_usuario),
            TTL,
        )
        return [{"id": r["id"], "nombre": r["nombre"], "icon": r["icon"], "color": r["color"]} for r in rows]

    def _subcategorias():
        rows = get_cached(
            id_usuario, "subcategorias",
            lambda: list_subcategorias_sql(id_usuario),
            TTL,
        )
        return [{"id": r["id"], "categoria_id": r["categoria_id"], "nombre": r["nombre"]} for r in rows]

    def _reglas():
        uid = id_usuario  # Capturar en closure para ThreadPoolExecutor
        rows = get_cached(
            uid, "reglas",
            lambda: list_reglas_comercio(uid),
            TTL,
        )
        return [_regla_to_raw(r) for r in rows]

    def _presupuestos():
        rows = get_cached(
            id_usuario, "presupuestos",
            lambda: list_presupuestos_sql(id_usuario, periodo_mes=None),
            TTL,
        )
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

    def _comercios_sql():
        return get_cached(
            id_usuario, "comercios",
            lambda: list_comercios_sql(id_usuario),
            TTL,
        )

    with ThreadPoolExecutor(max_workers=5) as ex:
        fut_cat = ex.submit(_categorias)
        fut_sub = ex.submit(_subcategorias)
        fut_reg = ex.submit(_reglas)
        fut_pre = ex.submit(_presupuestos)
        fut_com = ex.submit(_comercios_sql)

        categorias = fut_cat.result()
        subcategorias = fut_sub.result()
        reglas = fut_reg.result()
        presupuestos = fut_pre.result()
        comercios_sql = fut_com.result()

    # Comercios = SQL del usuario + virtuales (reglas + movimientos que no están en SQL)
    comercios_reglas = [str(r.get("comercio", r.get("patron", "")) or "").strip() for r in reglas if (r.get("comercio") or r.get("patron"))]
    comercios_movs = list_comercios_from_movimientos(id_usuario)
    all_names = list(dict.fromkeys([n for n in comercios_reglas + comercios_movs if n]))
    existing = {str(m.get("name", "")).lower(): m for m in comercios_sql}
    virtual = [
        {"id": f"comercio-{normalize_text(n).replace(' ', '_')}", "name": n}
        for n in all_names
        if n.lower() not in existing
    ]
    comercios = comercios_sql + virtual

    logger.info(
        "bootstrap id_usuario=%s categorias=%d subcategorias=%d reglas=%d presupuestos=%d comercios=%d",
        id_usuario, len(categorias), len(subcategorias), len(reglas), len(presupuestos), len(comercios),
    )

    return {
        "categorias": categorias,
        "subcategorias": subcategorias,
        "reglas": reglas,
        "presupuestos": presupuestos,
        "comercios": comercios,
    }
