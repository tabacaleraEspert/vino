"""
Comercios desde ReglaComercio (no tabla separada).
Cada regla = un comercio con id propio (ReglaComercio.Id).
Todos los comercios vienen del endpoint filtrado por Id_usuario.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.db.connection import get_connection
from app.db.regla_comercio import (
    list_reglas_comercio,
    create_regla_user,
    update_regla,
    delete_regla,
)
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

VIRTUAL_MERCHANT_PREFIX = "comercio-"


def _patron_norm_to_virtual_id(patron_norm: str) -> str:
    """PatronNorm -> comercio-XXX (solo para virtuales en bootstrap)."""
    if not patron_norm:
        return ""
    return f"{VIRTUAL_MERCHANT_PREFIX}{patron_norm.replace(' ', '_')}"


def _is_numeric_id(comercio_id: str) -> bool:
    """True si el id es numérico (ReglaComercio.Id)."""
    if not comercio_id:
        return False
    return str(comercio_id).strip().isdigit()


def list_comercios_sql(id_usuario: int) -> List[Dict[str, Any]]:
    """
    Lista comercios del usuario desde ReglaComercio.
    id = ReglaComercio.Id (numérico como string).
    """
    reglas = list_reglas_comercio(id_usuario)
    out = []
    for r in reglas:
        patron = r.get("patron") or r.get("comercio") or ""
        out.append({
            "id": str(r["id"]),
            "name": patron.strip(),
            "defaultCategoryId": str(r["categoria_id"]) if r.get("categoria_id") else None,
            "defaultSubcategoryId": str(r["subcategoria_id"]) if r.get("subcategoria_id") else None,
        })
    return out


def _comercio_id_to_patron_norm(comercio_id: str) -> Optional[str]:
    """comercio-XXX -> PatronNorm (para lookup por id legacy)."""
    if not comercio_id or not str(comercio_id).startswith(VIRTUAL_MERCHANT_PREFIX):
        return None
    suffix = str(comercio_id)[len(VIRTUAL_MERCHANT_PREFIX) :].replace("_", " ")
    return normalize_text(suffix) if suffix else None


def get_comercio_by_id_sql(id_usuario: int, comercio_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene comercio por id (ReglaComercio.Id numérico o comercio-XXX legacy)."""
    comercio_id = (comercio_id or "").strip()
    if not comercio_id:
        return None
    if _is_numeric_id(comercio_id):
        regla_id = int(comercio_id)
    else:
        patron_norm = _comercio_id_to_patron_norm(comercio_id)
        if not patron_norm:
            return None
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT Id FROM dbo.ReglaComercio WHERE Id_usuario = ? AND PatronNorm = ?",
                (id_usuario, patron_norm),
            )
            row = cur.fetchone()
        if not row:
            return None
        regla_id = row[0]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT rc.Id, rc.Patron, rc.Id_Categoria, rc.Id_SubCategoria
            FROM dbo.ReglaComercio rc
            WHERE rc.Id_usuario = ? AND rc.Id = ?
            """,
            (id_usuario, regla_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "name": str(row[1] or "").strip(),
        "defaultCategoryId": str(row[2]) if row[2] is not None else None,
        "defaultSubcategoryId": str(row[3]) if row[3] is not None else None,
    }


def get_comercio_id_by_name_sql(id_usuario: int, nombre: str) -> Optional[str]:
    """Resuelve nombre de comercio a id (ReglaComercio.Id). Retorna None si no existe."""
    patron_norm = normalize_text(nombre or "")
    if not patron_norm:
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT Id FROM dbo.ReglaComercio WHERE Id_usuario = ? AND PatronNorm = ?",
            (id_usuario, patron_norm),
        )
        row = cur.fetchone()
    return str(row[0]) if row else None


def get_comercio_ids_by_names_batch(
    id_usuario: int, nombres: List[str]
) -> Dict[str, str]:
    """
    Resuelve varios nombres a id en una sola query.
    Retorna {PatronNorm: comercio_id} para los que existen.
    """
    if not nombres:
        return {}
    seen: set = set()
    patron_norms: List[str] = []
    for n in nombres:
        n_clean = (n or "").strip()
        if not n_clean:
            continue
        pn = normalize_text(n_clean)
        if pn and pn not in seen:
            patron_norms.append(pn)
            seen.add(pn)
    if not patron_norms:
        return {}
    placeholders = ",".join("?" * len(patron_norms))
    params: List[Any] = [id_usuario] + patron_norms
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT Id, PatronNorm FROM dbo.ReglaComercio
            WHERE Id_usuario = ? AND PatronNorm IN ({placeholders})
            """,
            params,
        )
        rows = cur.fetchall()
    return {str(r[1]).strip(): str(r[0]) for r in rows}


def create_comercio_sql(
    id_usuario: int,
    nombre: str,
    default_category_id: Optional[str] = None,
    default_subcategory_id: Optional[str] = None,
    custom_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Crea comercio = crea ReglaComercio. Retorna con id = ReglaComercio.Id."""
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("Nombre es requerido")
    sub_id = (default_subcategory_id or "").strip() or None
    if not sub_id and default_category_id:
        from app.db.catalog import list_subcategorias_sql
        subs = list_subcategorias_sql(id_usuario, categoria_id=int(default_category_id))
        sub_id = str(subs[0]["id"]) if subs else None
    if not sub_id:
        raise KeyError("Se requiere defaultSubcategoryId o defaultCategoryId")
    created = create_regla_user(
        id_usuario=id_usuario,
        patron=nombre,
        id_subcategoria=sub_id,
    )
    return {
        "id": str(created["id"]),
        "name": nombre,
        "defaultCategoryId": created.get("categoria_id"),
        "defaultSubcategoryId": created.get("subcategoria_id"),
    }


def update_comercio_sql(
    id_usuario: int,
    comercio_id: str,
    nombre: Optional[str] = None,
    default_category_id: Optional[str] = None,
    default_subcategory_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Actualiza comercio = actualiza ReglaComercio por Id."""
    comercio_id = (comercio_id or "").strip()
    if not comercio_id or not _is_numeric_id(comercio_id):
        return None
    regla_id = int(comercio_id)
    sub_id = (default_subcategory_id or "").strip() or None
    if not sub_id and default_category_id:
        from app.db.catalog import list_subcategorias_sql
        subs = list_subcategorias_sql(id_usuario, categoria_id=int(default_category_id))
        sub_id = str(subs[0]["id"]) if subs else None
    updated = update_regla(
        id_usuario=id_usuario,
        regla_id=regla_id,
        patron=nombre,
        id_subcategoria=sub_id,
    )
    if not updated:
        return None
    return {
        "id": str(updated["id"]),
        "name": (updated.get("comercio") or updated.get("patron") or "").strip(),
        "defaultCategoryId": str(updated["categoria_id"]) if updated.get("categoria_id") else None,
        "defaultSubcategoryId": str(updated["subcategoria_id"]) if updated.get("subcategoria_id") else None,
    }


def delete_comercio_sql(id_usuario: int, comercio_id: str) -> bool:
    """Elimina comercio = elimina ReglaComercio por Id."""
    comercio_id = (comercio_id or "").strip()
    if not comercio_id or not _is_numeric_id(comercio_id):
        return False
    return delete_regla(id_usuario, int(comercio_id))
