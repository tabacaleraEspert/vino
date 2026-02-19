"""
Repository SQL para Categoria y SubCategoria (multi-tenant por Id_usuario).
Reemplaza lectura desde Google Sheets para estos catálogos.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.connection import get_connection

logger = logging.getLogger(__name__)

DEFAULT_ICON = "📁"
DEFAULT_COLOR = "#6b7280"


def _get_id_usuario(user: dict) -> int:
    """Extrae Id_usuario del payload JWT (sub = id de MaestroUsuarios)."""
    sub = user.get("sub") or user.get("id")
    if not sub:
        raise ValueError("No se pudo obtener Id_usuario del token")
    try:
        return int(sub)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Id_usuario inválido en token: {sub}") from e


def list_categorias_sql(id_usuario: int) -> List[Dict[str, Any]]:
    """
    Lista categorías del usuario desde Azure SQL.
    Formato compatible con frontend: { id, nombre, icon, color }.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT Id, Nombre, Icon, Color, [Timestamp]
            FROM dbo.Categoria
            WHERE Id_usuario = ?
            ORDER BY Nombre
            """,
            (id_usuario,),
        )
        rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "id": str(r[0]),
            "nombre": str(r[1] or "").strip() or "",
            "icon": str(r[2] or "").strip() or DEFAULT_ICON,
            "color": str(r[3] or "").strip() or DEFAULT_COLOR,
        })
    return out


def list_subcategorias_sql(
    id_usuario: int,
    categoria_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Lista subcategorías del usuario desde Azure SQL.
    Si categoria_id se pasa, filtra y valida que la categoría pertenezca al usuario.
    Formato: { id, categoria_id, nombre }.
    """
    if categoria_id is not None:
        # Validar que la categoría pertenezca al usuario
        cat = get_categoria_by_id_sql(id_usuario, categoria_id)
        if not cat:
            return []  # Categoría no existe o no pertenece al usuario
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT Id, Id_Categoria, Nombre_SubCategoria, [Timestamp]
                FROM dbo.SubCategoria
                WHERE Id_usuario = ? AND Id_Categoria = ?
                ORDER BY Nombre_SubCategoria
                """,
                (id_usuario, categoria_id),
            )
            rows = cur.fetchall()
    else:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT Id, Id_Categoria, Nombre_SubCategoria, [Timestamp]
                FROM dbo.SubCategoria
                WHERE Id_usuario = ?
                ORDER BY Id_Categoria, Nombre_SubCategoria
                """,
                (id_usuario,),
            )
            rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "id": str(r[0]),
            "categoria_id": str(r[1]),
            "nombre": str(r[2] or "").strip() or "",
        })
    return out


def get_categoria_by_id_sql(id_usuario: int, categoria_id: int | str) -> Optional[Dict[str, Any]]:
    """Obtiene una categoría por Id. Valida que pertenezca al usuario."""
    try:
        cat_id = int(categoria_id)
    except (TypeError, ValueError):
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT Id, Nombre, Icon, Color, [Timestamp]
            FROM dbo.Categoria
            WHERE Id_usuario = ? AND Id = ?
            """,
            (id_usuario, cat_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "nombre": str(row[1] or "").strip() or "",
        "icon": str(row[2] or "").strip() or DEFAULT_ICON,
        "color": str(row[3] or "").strip() or DEFAULT_COLOR,
    }


def get_subcategoria_by_id_sql(
    id_usuario: int,
    subcategoria_id: int | str,
    categoria_id: Optional[int | str] = None,
) -> Optional[Dict[str, Any]]:
    """Obtiene una subcategoría por Id. Valida que pertenezca al usuario."""
    try:
        sub_id = int(subcategoria_id)
    except (TypeError, ValueError):
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        if categoria_id is not None:
            cat_id = int(categoria_id) if isinstance(categoria_id, str) else categoria_id
            cur.execute(
                """
                SELECT Id, Id_Categoria, Nombre_SubCategoria, [Timestamp]
                FROM dbo.SubCategoria
                WHERE Id_usuario = ? AND Id = ? AND Id_Categoria = ?
                """,
                (id_usuario, sub_id, cat_id),
            )
        else:
            cur.execute(
                """
                SELECT Id, Id_Categoria, Nombre_SubCategoria, [Timestamp]
                FROM dbo.SubCategoria
                WHERE Id_usuario = ? AND Id = ?
                """,
                (id_usuario, sub_id),
            )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "categoria_id": str(row[1]),
        "nombre": str(row[2] or "").strip() or "",
    }


def create_categoria_sql(
    id_usuario: int,
    nombre: str,
    icon: str = DEFAULT_ICON,
    color: str = DEFAULT_COLOR,
) -> Dict[str, Any]:
    """Crea categoría en SQL. Devuelve el registro creado."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.Categoria (Id_usuario, Nombre, Icon, Color, [Timestamp])
            OUTPUT INSERTED.Id, INSERTED.Nombre, INSERTED.Icon, INSERTED.Color, INSERTED.[Timestamp]
            VALUES (?, ?, ?, ?, SYSUTCDATETIME())
            """,
            (id_usuario, nombre.strip(), icon.strip() or DEFAULT_ICON, color.strip() or DEFAULT_COLOR),
        )
        row = cur.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("No se pudo crear la categoría")
    return {
        "id": str(row[0]),
        "nombre": str(row[1] or "").strip(),
        "icon": str(row[2] or "").strip() or DEFAULT_ICON,
        "color": str(row[3] or "").strip() or DEFAULT_COLOR,
    }


def patch_categoria_sql(
    id_usuario: int,
    categoria_id: int | str,
    patch: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Actualiza categoría. Retorna el registro actualizado o None si no existe."""
    cat_id = int(categoria_id) if isinstance(categoria_id, str) else categoria_id
    updates = []
    params = []
    if "nombre" in patch or "name" in patch:
        v = (patch.get("nombre") or patch.get("name") or "").strip()
        updates.append("Nombre = ?")
        params.append(v)
    if "icon" in patch:
        updates.append("Icon = ?")
        params.append((patch.get("icon") or "").strip() or DEFAULT_ICON)
    if "color" in patch:
        updates.append("Color = ?")
        params.append((patch.get("color") or "").strip() or DEFAULT_COLOR)
    if not updates:
        return get_categoria_by_id_sql(id_usuario, cat_id)
    params.extend([id_usuario, cat_id])
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE dbo.Categoria
            SET {", ".join(updates)}, [Timestamp] = SYSUTCDATETIME()
            WHERE Id_usuario = ? AND Id = ?
            """,
            params,
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    return get_categoria_by_id_sql(id_usuario, cat_id)


def delete_categoria_sql(id_usuario: int, categoria_id: int | str) -> bool:
    """Elimina categoría. Retorna True si se eliminó."""
    cat_id = int(categoria_id) if isinstance(categoria_id, str) else categoria_id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM dbo.Categoria WHERE Id_usuario = ? AND Id = ?",
            (id_usuario, cat_id),
        )
        conn.commit()
        return cur.rowcount > 0


def create_subcategoria_sql(
    id_usuario: int,
    categoria_id: int | str,
    nombre: str,
) -> Dict[str, Any]:
    """Crea subcategoría. Valida que la categoría exista y pertenezca al usuario."""
    cat_id = int(categoria_id) if isinstance(categoria_id, str) else categoria_id
    if not get_categoria_by_id_sql(id_usuario, cat_id):
        raise KeyError("Categoría no encontrada")
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.SubCategoria (Id_usuario, Id_Categoria, Nombre_SubCategoria, [Timestamp])
            OUTPUT INSERTED.Id, INSERTED.Id_Categoria, INSERTED.Nombre_SubCategoria, INSERTED.[Timestamp]
            VALUES (?, ?, ?, SYSUTCDATETIME())
            """,
            (id_usuario, cat_id, nombre.strip()),
        )
        row = cur.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("No se pudo crear la subcategoría")
    return {
        "id": str(row[0]),
        "categoria_id": str(row[1]),
        "nombre": str(row[2] or "").strip(),
    }


def patch_subcategoria_sql(
    id_usuario: int,
    subcategoria_id: int | str,
    nombre: str,
) -> Optional[Dict[str, Any]]:
    """Actualiza subcategoría. Retorna el registro actualizado o None."""
    sub_id = int(subcategoria_id) if isinstance(subcategoria_id, str) else subcategoria_id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dbo.SubCategoria
            SET Nombre_SubCategoria = ?, [Timestamp] = SYSUTCDATETIME()
            WHERE Id_usuario = ? AND Id = ?
            """,
            (nombre.strip(), id_usuario, sub_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    return get_subcategoria_by_id_sql(id_usuario, sub_id)


def delete_subcategoria_sql(id_usuario: int, subcategoria_id: int | str) -> bool:
    """Elimina subcategoría. Retorna True si se eliminó."""
    sub_id = int(subcategoria_id) if isinstance(subcategoria_id, str) else subcategoria_id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM dbo.SubCategoria WHERE Id_usuario = ? AND Id = ?",
            (id_usuario, sub_id),
        )
        conn.commit()
        return cur.rowcount > 0
