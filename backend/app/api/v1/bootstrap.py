"""
Endpoint bootstrap: devuelve todos los catálogos en una sola llamada (async).
Reduce 5 requests del frontend a 1.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.categoria_repo import list_categorias, list_subcategorias
from app.repositories.regla_repo import list_reglas
from app.repositories.presupuesto_repo import list_presupuestos
from app.repositories.movimiento_repo import list_comercios_from_movimientos
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)
router = APIRouter()


def _regla_to_raw(r: dict) -> dict:
    return {
        "id": r["id"],
        "comercio": r.get("comercio", r.get("patron", "")),
        "categoria_id": r["categoria_id"],
        "categoria_nombre": r.get("categoria_nombre", ""),
        "subcategoria_id": r["subcategoria_id"],
        "subcategoria_nombre": r.get("subcategoria_nombre", ""),
        "timestamp": r.get("timestamp", ""),
    }


@router.get("")
async def bootstrap(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve categorias, subcategorias, reglas, presupuestos y comercios en una sola llamada."""
    logger.info("bootstrap start id_usuario=%s", id_usuario)

    # All queries use the same session (connection pooled, no ThreadPoolExecutor needed)
    categorias = await list_categorias(db, id_usuario)
    subcategorias = await list_subcategorias(db, id_usuario)
    reglas_raw = await list_reglas(db, id_usuario)
    presupuestos = await list_presupuestos(db, id_usuario)

    reglas = [_regla_to_raw(r) for r in reglas_raw]

    # Comercios: SQL + virtuales (from reglas + movimientos)
    # For now, use movimientos-based merchants
    comercios_movs = await list_comercios_from_movimientos(db, id_usuario)
    comercios_reglas = [
        str(r.get("comercio", r.get("patron", "")) or "").strip()
        for r in reglas if (r.get("comercio") or r.get("patron"))
    ]
    all_names = list(dict.fromkeys([n for n in comercios_reglas + comercios_movs if n]))
    comercios = [
        {"id": f"comercio-{normalize_text(n).replace(' ', '_')}", "name": n}
        for n in all_names
    ]

    logger.info(
        "bootstrap id_usuario=%s cat=%d sub=%d reg=%d pres=%d com=%d",
        id_usuario, len(categorias), len(subcategorias), len(reglas), len(presupuestos), len(comercios),
    )

    return {
        "categorias": categorias,
        "subcategorias": subcategorias,
        "reglas": reglas,
        "presupuestos": [
            {
                "id": r["id"],
                "mes_anio": r.get("mes_anio", ""),
                "categoria_id": r.get("categoria_id", ""),
                "categoria_nombre": r.get("categoria_nombre", ""),
                "subcategoria_id": r.get("subcategoria_id", ""),
                "subcategoria_nombre": r.get("subcategoria_nombre", ""),
                "monto": r.get("monto", 0),
            }
            for r in presupuestos
        ],
        "comercios": comercios,
    }
