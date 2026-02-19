"""
Repository SQL para Presupuestos (multi-tenant por Id_usuario).
Reemplaza lectura/escritura desde Google Sheets.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.db.catalog import get_categoria_by_id_sql, get_subcategoria_by_id_sql
from app.db.connection import get_connection
from app.utils.parse_utils import parse_periodo_mes, periodo_mes_to_mes_anio


def _check_categoria_user(id_usuario: int, id_categoria: int) -> bool:
    """Valida que la categoría pertenezca al usuario."""
    return get_categoria_by_id_sql(id_usuario, id_categoria) is not None


def _check_subcategoria_user(id_usuario: int, id_subcategoria: int) -> Optional[int]:
    """
    Valida que la subcategoría pertenezca al usuario.
    Retorna Id_Categoria real (desde SQL, no confiar en payload).
    """
    sub = get_subcategoria_by_id_sql(id_usuario, id_subcategoria)
    if not sub:
        return None
    return int(sub["categoria_id"])


def list_presupuestos_sql(
    id_usuario: int,
    periodo_mes: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Lista presupuestos del usuario.
    Si periodo_mes es None, devuelve todos los presupuestos del usuario.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        if periodo_mes is not None:
            cur.execute(
                """
                SELECT
                  p.Id,
                  p.PeriodoMes,
                  p.Id_Categoria,
                  c.Nombre AS Nombre_Categoria,
                  p.Id_SubCategoria,
                  sc.Nombre_SubCategoria,
                  p.Monto,
                  p.[Timestamp]
                FROM dbo.Presupuestos p
                LEFT JOIN dbo.Categoria c
                  ON c.Id = p.Id_Categoria AND c.Id_usuario = p.Id_usuario
                LEFT JOIN dbo.SubCategoria sc
                  ON sc.Id = p.Id_SubCategoria AND sc.Id_usuario = p.Id_usuario
                WHERE p.Id_usuario = ? AND p.PeriodoMes = ?
                ORDER BY c.Nombre, sc.Nombre_SubCategoria
                """,
                (id_usuario, periodo_mes),
            )
        else:
            cur.execute(
                """
                SELECT
                  p.Id,
                  p.PeriodoMes,
                  p.Id_Categoria,
                  c.Nombre AS Nombre_Categoria,
                  p.Id_SubCategoria,
                  sc.Nombre_SubCategoria,
                  p.Monto,
                  p.[Timestamp]
                FROM dbo.Presupuestos p
                LEFT JOIN dbo.Categoria c
                  ON c.Id = p.Id_Categoria AND c.Id_usuario = p.Id_usuario
                LEFT JOIN dbo.SubCategoria sc
                  ON sc.Id = p.Id_SubCategoria AND sc.Id_usuario = p.Id_usuario
                WHERE p.Id_usuario = ?
                ORDER BY p.PeriodoMes DESC, c.Nombre, sc.Nombre_SubCategoria
                """,
                (id_usuario,),
            )
        rows = cur.fetchall()
    out = []
    for r in rows:
        row_periodo = r[1]  # PeriodoMes de la fila
        mes_anio = periodo_mes_to_mes_anio(row_periodo) if row_periodo else ""
        out.append({
            "id": str(r[0]),
            "mesAño": mes_anio,
            "mes_anio": mes_anio,
            "idCategoria": str(r[2]) if r[2] is not None else "",
            "categoria_id": str(r[2]) if r[2] is not None else "",
            "Nombre_Categoria": str(r[3] or "").strip(),
            "categoria_nombre": str(r[3] or "").strip(),
            "idSubcategoria": str(r[4]) if r[4] is not None else "",
            "subcategoria_id": str(r[4]) if r[4] is not None else "",
            "Nombre_SubCategoria": str(r[5] or "").strip(),
            "subcategoria_nombre": str(r[5] or "").strip(),
            "Monto": float(r[6]) if r[6] is not None else 0.0,
            "monto": str(r[6]) if r[6] is not None else "0",
            "Timestamp": str(r[7]) if r[7] else "",
        })
    return out


def upsert_presupuesto_sql(
    id_usuario: int,
    periodo_mes: date,
    id_categoria: Optional[int],
    id_subcategoria: Optional[int],
    monto: float,
) -> Dict[str, Any]:
    """
    UPSERT por clave (Id_usuario, PeriodoMes, Id_Categoria, Id_SubCategoria).
    Si id_subcategoria viene, resuelve id_categoria desde SubCategoria.
    Valida pertenencia al usuario.
    """
    if monto <= 0:
        raise ValueError("Monto debe ser mayor a 0")

    cat_id = id_categoria
    sub_id = id_subcategoria

    if sub_id is not None:
        # Resolver Id_Categoria real desde SubCategoria (no confiar en payload)
        cat_id = _check_subcategoria_user(id_usuario, sub_id)
        if cat_id is None:
            raise ValueError("Subcategoría no encontrada o no pertenece al usuario")
    else:
        if cat_id is None:
            raise ValueError("Debe indicar idCategoria o idSubcategoria")
        if not _check_categoria_user(id_usuario, cat_id):
            raise ValueError("Categoría no encontrada o no pertenece al usuario")

    with get_connection() as conn:
        cur = conn.cursor()
        # UPDATE si existe (evita problemas con NULL en MERGE)
        if sub_id is not None:
            cur.execute(
                """
                UPDATE dbo.Presupuestos
                SET Monto = ?, Id_Categoria = ?, [Timestamp] = SYSUTCDATETIME()
                WHERE Id_usuario = ? AND PeriodoMes = ? AND Id_SubCategoria = ?
                """,
                (monto, cat_id, id_usuario, periodo_mes, sub_id),
            )
        else:
            cur.execute(
                """
                UPDATE dbo.Presupuestos
                SET Monto = ?, [Timestamp] = SYSUTCDATETIME()
                WHERE Id_usuario = ? AND PeriodoMes = ? AND Id_Categoria = ? AND Id_SubCategoria IS NULL
                """,
                (monto, id_usuario, periodo_mes, cat_id),
            )
        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO dbo.Presupuestos (Id_usuario, PeriodoMes, Id_Categoria, Id_SubCategoria, Monto, [Timestamp])
                VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME())
                """,
                (id_usuario, periodo_mes, cat_id, sub_id, monto),
            )
        conn.commit()

    # Leer el registro actualizado/insertado
    rows = list_presupuestos_sql(id_usuario, periodo_mes)
    for r in rows:
        if (str(r["categoria_id"]) == str(cat_id) and
            (str(r["subcategoria_id"]) == str(sub_id) if sub_id else r["subcategoria_id"] == "")):
            return r
    raise RuntimeError("UPSERT OK pero no se pudo recuperar el registro")


def delete_presupuesto_sql(id_usuario: int, presupuesto_id: int | str) -> bool:
    """Elimina presupuesto por Id. Retorna True si se eliminó."""
    pid = int(presupuesto_id) if isinstance(presupuesto_id, str) else presupuesto_id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM dbo.Presupuestos WHERE Id_usuario = ? AND Id = ?",
            (id_usuario, pid),
        )
        conn.commit()
        return cur.rowcount > 0


def get_presupuesto_by_id_sql(id_usuario: int, presupuesto_id: int | str) -> Optional[Dict[str, Any]]:
    """Obtiene presupuesto por Id."""
    pid = int(presupuesto_id) if isinstance(presupuesto_id, str) else presupuesto_id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.Id, p.PeriodoMes, p.Id_Categoria, c.Nombre, p.Id_SubCategoria, sc.Nombre_SubCategoria, p.Monto, p.[Timestamp]
            FROM dbo.Presupuestos p
            LEFT JOIN dbo.Categoria c ON c.Id = p.Id_Categoria AND c.Id_usuario = p.Id_usuario
            LEFT JOIN dbo.SubCategoria sc ON sc.Id = p.Id_SubCategoria AND sc.Id_usuario = p.Id_usuario
            WHERE p.Id_usuario = ? AND p.Id = ?
            """,
            (id_usuario, pid),
        )
        row = cur.fetchone()
    if not row:
        return None
    periodo = row[1]
    mes_anio = periodo_mes_to_mes_anio(periodo) if periodo else ""
    return {
        "id": str(row[0]),
        "mesAño": mes_anio,
        "mes_anio": mes_anio,
        "categoria_id": str(row[2]) if row[2] is not None else "",
        "categoria_nombre": str(row[3] or "").strip(),
        "subcategoria_id": str(row[4]) if row[4] is not None else "",
        "subcategoria_nombre": str(row[5] or "").strip(),
        "monto": str(row[6]) if row[6] is not None else "0",
        "Monto": float(row[6]) if row[6] is not None else 0.0,
    }


def patch_presupuesto_sql(
    id_usuario: int,
    presupuesto_id: int | str,
    monto: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Actualiza monto del presupuesto. Retorna el registro actualizado."""
    pres = get_presupuesto_by_id_sql(id_usuario, presupuesto_id)
    if not pres:
        return None
    if monto is None:
        return pres
    if monto <= 0:
        raise ValueError("Monto debe ser mayor a 0")
    pid = int(presupuesto_id) if isinstance(presupuesto_id, str) else presupuesto_id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE dbo.Presupuestos SET Monto = ?, [Timestamp] = SYSUTCDATETIME() WHERE Id_usuario = ? AND Id = ?",
            (monto, id_usuario, pid),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    return get_presupuesto_by_id_sql(id_usuario, presupuesto_id)
