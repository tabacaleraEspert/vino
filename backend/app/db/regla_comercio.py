"""
Repository SQL para ReglaComercio (reglas de categorización por comercio).
Matching CONTAINS sobre razón social (merchant descriptor).
Multi-tenant por Id_usuario.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.db.connection import get_connection
from app.db.catalog import (
    get_categoria_by_id_sql,
    get_subcategoria_by_id_sql,
    create_categoria_sql,
    create_subcategoria_sql,
)
from app.utils.normalize import normalize_text, patron_sugerido

logger = logging.getLogger(__name__)

CATEGORIA_OTROS = "Otros"
SUBCATEGORIA_NO_CATEGORIZADOS = "Gastos no categorizados"
PRIORIDAD_AUTO = 200
PRIORIDAD_USER_DEFAULT = 100


def _get_or_create_otros_defaults(id_usuario: int) -> Tuple[int, int]:
    """
    Obtiene o crea Categoría "Otros" y SubCategoría "Gastos no categorizados".
    Retorna (id_categoria, id_subcategoria).
    """
    from app.db.catalog import list_categorias_sql, list_subcategorias_sql

    cats = list_categorias_sql(id_usuario)
    otros = next((c for c in cats if (c.get("nombre") or "").strip().lower() == "otros"), None)
    if otros:
        id_cat = int(otros["id"])
    else:
        created = create_categoria_sql(id_usuario, CATEGORIA_OTROS)
        id_cat = int(created["id"])

    subs = list_subcategorias_sql(id_usuario, categoria_id=id_cat)
    no_cat = next(
        (s for s in subs if (s.get("nombre") or "").strip().lower() == SUBCATEGORIA_NO_CATEGORIZADOS.lower()),
        None,
    )
    if no_cat:
        id_sub = int(no_cat["id"])
    else:
        created_sub = create_subcategoria_sql(id_usuario, id_cat, SUBCATEGORIA_NO_CATEGORIZADOS)
        id_sub = int(created_sub["id"])

    return id_cat, id_sub


def list_reglas_comercio(id_usuario: int) -> List[Dict[str, Any]]:
    """
    Lista reglas del usuario con nombres de categoría/subcategoría.
    Formato compatible con ReglaRaw: id, comercio (patron), ejemploRazonSocial, categoria_id, subcategoria_id, etc.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT rc.Id, rc.Patron, rc.EjemploRazonSocial, rc.Id_Categoria, c.Nombre,
                   rc.Id_SubCategoria, sc.Nombre_SubCategoria,
                   rc.Prioridad, rc.Activa, rc.Confianza, rc.ActualizadoEn
            FROM dbo.ReglaComercio rc
            JOIN dbo.Categoria c ON c.Id = rc.Id_Categoria AND c.Id_usuario = rc.Id_usuario
            JOIN dbo.SubCategoria sc ON sc.Id = rc.Id_SubCategoria AND sc.Id_usuario = rc.Id_usuario
            WHERE rc.Id_usuario = ?
            ORDER BY rc.Prioridad ASC, LEN(rc.PatronNorm) DESC, rc.ActualizadoEn DESC
            """,
            (id_usuario,),
        )
        rows = cur.fetchall()

    out = []
    for r in rows:
        out.append({
            "id": str(r[0]),
            "patron": str(r[1] or "").strip(),
            "ejemploRazonSocial": str(r[2] or "").strip() if r[2] else None,
            "idCategoria": r[3],
            "nombreCategoria": str(r[4] or "").strip(),
            "idSubcategoria": r[5],
            "nombreSubcategoria": str(r[6] or "").strip(),
            "prioridad": r[7] or 100,
            "activa": bool(r[8]) if r[8] is not None else True,
            "confianza": str(r[9] or "AUTO").strip(),
            "actualizadoEn": r[10].isoformat() if r[10] else None,
            # Compatibilidad ReglaRaw
            "comercio": str(r[1] or "").strip(),
            "categoria_id": str(r[3]),
            "categoria_nombre": str(r[4] or "").strip(),
            "subcategoria_id": str(r[5]),
            "subcategoria_nombre": str(r[6] or "").strip(),
            "timestamp": r[10].isoformat() if r[10] else None,
        })
    return out


def create_regla_user(
    id_usuario: int,
    patron: str,
    id_subcategoria: int | str,
    ejemplo_razon_social: Optional[str] = None,
    prioridad: int = PRIORIDAD_USER_DEFAULT,
    activa: bool = True,
) -> Dict[str, Any]:
    """
    Crea regla manualmente (Confianza='USER').
    Resuelve idCategoria desde SubCategoria.
    """
    patron = (patron or "").strip()
    if not patron:
        raise ValueError("patron es requerido")

    sub = get_subcategoria_by_id_sql(id_usuario, id_subcategoria)
    if not sub:
        raise KeyError("Subcategoría no encontrada o no pertenece al usuario")

    id_cat = int(sub["categoria_id"])
    patron_norm = normalize_text(patron)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.ReglaComercio
            (Id_usuario, Patron, PatronNorm, EjemploRazonSocial, Id_Categoria, Id_SubCategoria, Prioridad, Activa, Confianza)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'USER')
            OUTPUT INSERTED.Id, INSERTED.Patron, INSERTED.PatronNorm, INSERTED.EjemploRazonSocial,
                   INSERTED.Id_Categoria, INSERTED.Id_SubCategoria, INSERTED.Prioridad, INSERTED.Activa, INSERTED.Confianza, INSERTED.ActualizadoEn
            """,
            (
                id_usuario,
                patron,
                patron_norm,
                (ejemplo_razon_social or "").strip() or None,
                id_cat,
                int(sub["id"]),
                prioridad,
                1 if activa else 0,
            ),
        )
        row = cur.fetchone()
        conn.commit()

    if not row:
        raise RuntimeError("No se pudo crear la regla")

    cat = get_categoria_by_id_sql(id_usuario, id_cat)
    return {
        "id": str(row[0]),
        "patron": str(row[1] or "").strip(),
        "ejemploRazonSocial": str(row[2] or "").strip() if row[2] else None,
        "idCategoria": row[4],
        "nombreCategoria": (cat or {}).get("nombre", ""),
        "idSubcategoria": row[5],
        "nombreSubcategoria": sub.get("nombre", ""),
        "prioridad": row[6],
        "activa": bool(row[7]),
        "confianza": "USER",
        "actualizadoEn": row[9].isoformat() if row[9] else None,
        "comercio": str(row[1] or "").strip(),
        "categoria_id": str(row[4]),
        "categoria_nombre": (cat or {}).get("nombre", ""),
        "subcategoria_id": str(row[5]),
        "subcategoria_nombre": sub.get("nombre", ""),
    }


def update_regla(
    id_usuario: int,
    regla_id: int | str,
    patron: Optional[str] = None,
    id_subcategoria: Optional[int | str] = None,
    prioridad: Optional[int] = None,
    activa: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """
    Actualiza regla. Si el usuario edita, setea Confianza='USER'.
    """
    regla_id = int(regla_id) if isinstance(regla_id, str) else regla_id

    updates = []
    params: List[Any] = []

    if patron is not None:
        patron = patron.strip()
        if not patron:
            raise ValueError("patron no puede estar vacío")
        patron_norm = normalize_text(patron)
        updates.append("Patron = ?, PatronNorm = ?")
        params.extend([patron, patron_norm])

    if id_subcategoria is not None:
        sub = get_subcategoria_by_id_sql(id_usuario, id_subcategoria)
        if not sub:
            raise KeyError("Subcategoría no encontrada")
        updates.append("Id_Categoria = ?, Id_SubCategoria = ?")
        params.extend([int(sub["categoria_id"]), int(sub["id"])])

    if prioridad is not None:
        updates.append("Prioridad = ?")
        params.append(prioridad)

    if activa is not None:
        updates.append("Activa = ?")
        params.append(1 if activa else 0)

    updates.append("Confianza = 'USER'")
    updates.append("ActualizadoEn = SYSUTCDATETIME()")

    if len(updates) <= 2:  # solo Confianza y ActualizadoEn
        # No hay cambios sustantivos
        return get_regla_by_id(id_usuario, regla_id)

    params.extend([id_usuario, regla_id])

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE dbo.ReglaComercio
            SET {", ".join(updates)}
            WHERE Id_usuario = ? AND Id = ?
            """,
            params,
        )
        conn.commit()
        if cur.rowcount == 0:
            return None

    return get_regla_by_id(id_usuario, regla_id)


def get_regla_by_id(id_usuario: int, regla_id: int | str) -> Optional[Dict[str, Any]]:
    """Obtiene una regla por Id."""
    regla_id = int(regla_id) if isinstance(regla_id, str) else regla_id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT rc.Id, rc.Patron, rc.EjemploRazonSocial, rc.Id_Categoria, c.Nombre,
                   rc.Id_SubCategoria, sc.Nombre_SubCategoria,
                   rc.Prioridad, rc.Activa, rc.Confianza, rc.ActualizadoEn
            FROM dbo.ReglaComercio rc
            JOIN dbo.Categoria c ON c.Id = rc.Id_Categoria AND c.Id_usuario = rc.Id_usuario
            JOIN dbo.SubCategoria sc ON sc.Id = rc.Id_SubCategoria AND sc.Id_usuario = rc.Id_usuario
            WHERE rc.Id_usuario = ? AND rc.Id = ?
            """,
            (id_usuario, regla_id),
        )
        row = cur.fetchone()

    if not row:
        return None

    return {
        "id": str(row[0]),
        "patron": str(row[1] or "").strip(),
        "ejemploRazonSocial": str(row[2] or "").strip() if row[2] else None,
        "idCategoria": row[3],
        "nombreCategoria": str(row[4] or "").strip(),
        "idSubcategoria": row[5],
        "nombreSubcategoria": str(row[6] or "").strip(),
        "prioridad": row[7],
        "activa": bool(row[8]),
        "confianza": str(row[9] or "AUTO").strip(),
        "actualizadoEn": row[10].isoformat() if row[10] else None,
        "comercio": str(row[1] or "").strip(),
        "categoria_id": str(row[3]),
        "categoria_nombre": str(row[4] or "").strip(),
        "subcategoria_id": str(row[5]),
        "subcategoria_nombre": str(row[6] or "").strip(),
        "timestamp": row[10].isoformat() if row[10] else None,
    }


def _fetch_reglas_activas_para_resolve(id_usuario: int) -> List[Dict[str, Any]]:
    """Trae reglas activas con PatronNorm para matching en Python."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT Id, PatronNorm, Prioridad, Confianza, Id_Categoria, Id_SubCategoria, ActualizadoEn
            FROM dbo.ReglaComercio
            WHERE Id_usuario = ? AND Activa = 1
            ORDER BY Prioridad ASC, LEN(PatronNorm) DESC
            """,
            (id_usuario,),
        )
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "patron_norm": str(r[1] or "").strip(),
            "prioridad": r[2] or 100,
            "confianza": str(r[3] or "AUTO").strip(),
            "id_categoria": r[4],
            "id_subcategoria": r[5],
            "actualizado_en": r[6],
        }
        for r in rows
    ]


def _rank_reglas(matches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Orden: 1) Prioridad ASC, 2) LEN(PatronNorm) DESC, 3) USER antes AUTO, 4) ActualizadoEn DESC.
    """
    if not matches:
        return None

    def key(m):
        return (
            m["prioridad"],
            -len(m["patron_norm"]),
            0 if m["confianza"] == "USER" else 1,
            -(m["actualizado_en"].timestamp() if m["actualizado_en"] else 0),
        )

    best = min(matches, key=key)
    return best


def resolve_regla(
    id_usuario: int,
    razon_social: str,
    create_auto_if_no_match: bool = True,
) -> Dict[str, Any]:
    """
    Resuelve categoría/subcategoría para una razón social.
    - Si hay match: devuelve ids + regla_id.
    - Si no hay match y create_auto_if_no_match: crea regla AUTO y devuelve ids + created_auto=True.
    - Si no hay match y no create: devuelve ids de Otros/Gastos no categorizados (sin crear regla).
    """
    merchant_norm = normalize_text(razon_social or "")
    if not merchant_norm:
        id_cat, id_sub = _get_or_create_otros_defaults(id_usuario)
        return {
            "id_categoria": id_cat,
            "id_subcategoria": id_sub,
            "regla_id": None,
            "created_auto": False,
            "nombre_categoria": CATEGORIA_OTROS,
            "nombre_subcategoria": SUBCATEGORIA_NO_CATEGORIZADOS,
        }

    reglas = _fetch_reglas_activas_para_resolve(id_usuario)
    matches = [r for r in reglas if r["patron_norm"] and r["patron_norm"] in merchant_norm]

    best = _rank_reglas(matches)
    if best:
        cat = get_categoria_by_id_sql(id_usuario, best["id_categoria"])
        sub = get_subcategoria_by_id_sql(id_usuario, best["id_subcategoria"])
        return {
            "id_categoria": best["id_categoria"],
            "id_subcategoria": best["id_subcategoria"],
            "regla_id": best["id"],
            "created_auto": False,
            "nombre_categoria": (cat or {}).get("nombre", ""),
            "nombre_subcategoria": (sub or {}).get("nombre", ""),
        }

    id_cat, id_sub = _get_or_create_otros_defaults(id_usuario)
    patron_sug = patron_sugerido(merchant_norm)

    regla_id_auto: Optional[int] = None
    if create_auto_if_no_match:
        regla_id_auto = _create_regla_auto_idempotente(
            id_usuario=id_usuario,
            patron_sugerido=patron_sug,
            ejemplo_razon_social=razon_social.strip()[:300],
            id_categoria=id_cat,
            id_subcategoria=id_sub,
        )

    cat = get_categoria_by_id_sql(id_usuario, id_cat)
    sub = get_subcategoria_by_id_sql(id_usuario, id_sub)
    return {
        "id_categoria": id_cat,
        "id_subcategoria": id_sub,
        "regla_id": regla_id_auto,
        "created_auto": create_auto_if_no_match,
        "nombre_categoria": (cat or {}).get("nombre", CATEGORIA_OTROS),
        "nombre_subcategoria": (sub or {}).get("nombre", SUBCATEGORIA_NO_CATEGORIZADOS),
    }


def get_regla_id_by_patron_norm(id_usuario: int, patron_norm: str) -> Optional[int]:
    """Obtiene Id de regla por PatronNorm (para obtener id tras crear AUTO)."""
    if not patron_norm:
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT Id FROM dbo.ReglaComercio WHERE Id_usuario = ? AND PatronNorm = ?",
            (id_usuario, patron_norm),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _create_regla_auto_idempotente(
    id_usuario: int,
    patron_sugerido: str,
    ejemplo_razon_social: str,
    id_categoria: int,
    id_subcategoria: int,
) -> Optional[int]:
    """Crea regla AUTO si no existe PatronNorm. Retorna Id de la regla (o None)."""
    patron_norm = normalize_text(patron_sugerido)
    if not patron_norm:
        return None

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM dbo.ReglaComercio WHERE Id_usuario = ? AND PatronNorm = ?)
            INSERT INTO dbo.ReglaComercio
            (Id_usuario, Patron, PatronNorm, EjemploRazonSocial, Id_Categoria, Id_SubCategoria, Prioridad, Activa, Confianza)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'AUTO')
            """,
            (
                id_usuario,
                patron_norm,
                id_usuario,
                patron_sugerido[:120],
                patron_norm,
                (ejemplo_razon_social[:300] if ejemplo_razon_social else None),
                id_categoria,
                id_subcategoria,
                PRIORIDAD_AUTO,
            ),
        )
        conn.commit()
    logger.info("ReglaComercio: regla AUTO creada para patron_norm=%s usuario=%s", patron_norm, id_usuario)
    return get_regla_id_by_patron_norm(id_usuario, patron_norm)


def delete_regla(id_usuario: int, regla_id: int | str) -> bool:
    """Elimina regla. Retorna True si se eliminó."""
    regla_id = int(regla_id) if isinstance(regla_id, str) else regla_id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM dbo.ReglaComercio WHERE Id_usuario = ? AND Id = ?",
            (id_usuario, regla_id),
        )
        conn.commit()
        return cur.rowcount > 0
