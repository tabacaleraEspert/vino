"""
Repository SQL para Movimientos (gastos/ingresos).
Multi-tenant por Id_usuario. Reemplaza Google Sheets.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.db.catalog import (
    get_categoria_by_id_sql,
    get_subcategoria_by_id_sql,
    list_categorias_sql,
    list_subcategorias_sql,
)
from app.db.connection import get_connection
from app.utils.parse_utils import parse_date_flex, parse_money

logger = logging.getLogger(__name__)


def _row_to_item(r: tuple, col_names: List[str]) -> Dict[str, Any]:
    """Convierte fila SQL a dict con nombres de columna."""
    out: Dict[str, Any] = {}
    for i, name in enumerate(col_names):
        if i < len(r):
            val = r[i]
            if isinstance(val, Decimal):
                val = float(val)
            elif isinstance(val, datetime):
                val = val.isoformat() if val else None
            elif isinstance(val, date) and not isinstance(val, datetime):
                val = val.strftime("%Y-%m-%d") if val else None
            out[name] = val
    return out


def _movimiento_to_api(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formato compatible con frontend (MovimientoItem / MovimientoRaw).
    Incluye id, fecha, tipo, moneda, monto, comercio, descripcion, categoria, subcategoria, medio_pago.
    """
    fecha = row.get("Fecha")
    if isinstance(fecha, date):
        fecha = fecha.strftime("%Y-%m-%d")
    tipo_raw = str(row.get("TipoMovimiento", "")).strip().lower()
    tipo = "Ingreso" if tipo_raw == "ingreso" else "Gasto"
    monto = row.get("Monto")
    if monto is not None:
        monto = round(float(monto), 2)

    return {
        "id": str(row.get("Id", "")),
        "Id": row.get("Id"),
        "fecha": fecha or "",
        "Fecha": fecha or "",
        "timestamp": row.get("Timestamp"),
        "Timestamp": row.get("Timestamp"),
        "tipo": tipo,
        "moneda": str(row.get("Moneda", "")).strip(),
        "Moneda": str(row.get("Moneda", "")).strip(),
        "monto": monto,
        "Monto": monto,
        "comercio": str(row.get("Descripcion", "") or "").strip(),
        "Comercio": str(row.get("Descripcion", "") or "").strip(),
        "descripcion": str(row.get("Descripcion", "") or "").strip(),
        "Descripcion": str(row.get("Descripcion", "") or "").strip(),
        "categoria": str(row.get("Nombre_Categoria", "") or "").strip(),
        "Nombre_Categoria": str(row.get("Nombre_Categoria", "") or "").strip(),
        "subcategoria": str(row.get("Nombre_SubCategoria", "") or "").strip(),
        "Nombre_SubCategoria": str(row.get("Nombre_SubCategoria", "") or "").strip(),
        "medio_pago": str(row.get("Id_Medio_Pago_Final", "") or ""),
        "idCategoria": str(row.get("Id_Categoria", "")) if row.get("Id_Categoria") else None,
        "idSubcategoria": str(row.get("Id_SubCategoria", "")) if row.get("Id_SubCategoria") else None,
        "Id_Categoria": row.get("Id_Categoria"),
        "Id_SubCategoria": row.get("Id_SubCategoria"),
        "MedioCarga": str(row.get("MedioCarga", "")).strip(),
        "Id_Credito_Debito": row.get("Id_Credito_Debito"),
        "Id_Medio_Pago_Final": row.get("Id_Medio_Pago_Final"),
        "Origen": row.get("Origen"),
        "Origen_Id": row.get("Origen_Id"),
    }


def _resolve_categoria_subcategoria_from_names(
    id_usuario: int,
    nombre_categoria: Optional[str],
    nombre_subcategoria: Optional[str],
) -> tuple[Optional[int], Optional[int]]:
    """Resuelve nombres a IDs (compatibilidad con payload legacy)."""
    if not nombre_categoria and not nombre_subcategoria:
        return None, None
    cats = list_categorias_sql(id_usuario)
    cat = next(
        (c for c in cats if (c.get("nombre") or "").strip().lower() == (nombre_categoria or "").strip().lower()),
        None,
    )
    if not cat:
        return None, None
    id_cat = int(cat["id"])
    if not nombre_subcategoria:
        return id_cat, None
    subs = list_subcategorias_sql(id_usuario, categoria_id=id_cat)
    sub = next(
        (s for s in subs if (s.get("nombre") or "").strip().lower() == (nombre_subcategoria or "").strip().lower()),
        None,
    )
    if not sub:
        return id_cat, None
    return id_cat, int(sub["id"])


def _validate_categoria_subcategoria(
    id_usuario: int,
    id_categoria: Optional[int],
    id_subcategoria: Optional[int],
) -> tuple[Optional[int], Optional[int]]:
    """
    Valida que cat/subcat pertenezcan al usuario.
    Si id_subcategoria viene, deriva id_categoria desde SubCategoria.
    Retorna (id_categoria_valido, id_subcategoria_valido).
    """
    if id_subcategoria is not None:
        sub = get_subcategoria_by_id_sql(id_usuario, id_subcategoria)
        if not sub:
            raise ValueError("Subcategoría no encontrada o no pertenece al usuario")
        id_cat_real = int(sub["categoria_id"])
        if id_categoria is not None and id_categoria != id_cat_real:
            raise ValueError("Id_SubCategoria no pertenece a Id_Categoria indicado")
        return id_cat_real, int(sub["id"])
    if id_categoria is not None:
        cat = get_categoria_by_id_sql(id_usuario, id_categoria)
        if not cat:
            raise ValueError("Categoría no encontrada o no pertenece al usuario")
        return id_categoria, None
    return None, None


def list_movimientos(
    id_usuario: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    tipo: Optional[str] = None,
    categoria_id: Optional[int] = None,
    subcategoria_id: Optional[int] = None,
    medio_carga: Optional[str] = None,
    moneda: Optional[str] = None,
    comercio: Optional[str] = None,
    q: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[Dict[str, Any]], int]:
    """
    Lista movimientos del usuario con filtros y paginación.
    Retorna (items, total_count).
    """
    params: List[Any] = [id_usuario]
    conditions = ["m.Id_usuario = ?"]

    if from_date:
        conditions.append("m.Fecha >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("m.Fecha <= ?")
        params.append(to_date)
    if tipo:
        conditions.append("m.TipoMovimiento = ?")
        params.append(tipo.strip())
    if categoria_id is not None:
        conditions.append("m.Id_Categoria = ?")
        params.append(categoria_id)
    if subcategoria_id is not None:
        conditions.append("m.Id_SubCategoria = ?")
        params.append(subcategoria_id)
    if medio_carga:
        conditions.append("m.MedioCarga = ?")
        params.append(medio_carga.strip())
    if moneda:
        conditions.append("m.Moneda = ?")
        params.append(moneda.strip().upper())
    if min_amount is not None:
        conditions.append("m.Monto >= ?")
        params.append(min_amount)
    if max_amount is not None:
        conditions.append("m.Monto <= ?")
        params.append(max_amount)
    if comercio or q:
        terms = []
        if comercio:
            terms.append("m.Descripcion LIKE ?")
            params.append(f"%{comercio.strip()}%")
        if q:
            terms.append("m.Descripcion LIKE ?")
            params.append(f"%{q.strip()}%")
        conditions.append("(" + " OR ".join(terms) + ")")

    where = " AND ".join(conditions)

    # Total count (usa alias m para consistencia con WHERE)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT COUNT(*) FROM dbo.movimientos m WHERE {where}",
            params,
        )
        total = cur.fetchone()[0] or 0

        # Data con JOIN para nombres
        cur.execute(
            f"""
            SELECT
              m.Id, m.Fecha, m.[Timestamp], m.MedioCarga, m.TipoMovimiento, m.Moneda, m.Monto,
              m.Id_Credito_Debito, m.Id_Medio_Pago_Final, m.Descripcion,
              m.Id_Categoria, m.Id_SubCategoria, m.Origen, m.Origen_Id,
              c.Nombre AS Nombre_Categoria,
              sc.Nombre_SubCategoria
            FROM dbo.movimientos m
            LEFT JOIN dbo.Categoria c ON c.Id = m.Id_Categoria AND c.Id_usuario = m.Id_usuario
            LEFT JOIN dbo.SubCategoria sc ON sc.Id = m.Id_SubCategoria AND sc.Id_usuario = m.Id_usuario
            WHERE {where}
            ORDER BY m.Fecha DESC, m.Id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """,
            params + [offset, limit],
        )
        rows = cur.fetchall()

    col_names = [
        "Id", "Fecha", "Timestamp", "MedioCarga", "TipoMovimiento", "Moneda", "Monto",
        "Id_Credito_Debito", "Id_Medio_Pago_Final", "Descripcion",
        "Id_Categoria", "Id_SubCategoria", "Origen", "Origen_Id",
        "Nombre_Categoria", "Nombre_SubCategoria",
    ]
    items = [_movimiento_to_api(_row_to_item(r, col_names)) for r in rows]
    return items, total


def get_movimiento(id_usuario: int, mov_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un movimiento por Id."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              m.Id, m.Fecha, m.[Timestamp], m.MedioCarga, m.TipoMovimiento, m.Moneda, m.Monto,
              m.Id_Credito_Debito, m.Id_Medio_Pago_Final, m.Descripcion,
              m.Id_Categoria, m.Id_SubCategoria, m.Origen, m.Origen_Id,
              c.Nombre AS Nombre_Categoria,
              sc.Nombre_SubCategoria
            FROM dbo.movimientos m
            LEFT JOIN dbo.Categoria c ON c.Id = m.Id_Categoria AND c.Id_usuario = m.Id_usuario
            LEFT JOIN dbo.SubCategoria sc ON sc.Id = m.Id_SubCategoria AND sc.Id_usuario = m.Id_usuario
            WHERE m.Id_usuario = ? AND m.Id = ?
            """,
            (id_usuario, mov_id),
        )
        row = cur.fetchone()

    if not row:
        return None

    col_names = [
        "Id", "Fecha", "Timestamp", "MedioCarga", "TipoMovimiento", "Moneda", "Monto",
        "Id_Credito_Debito", "Id_Medio_Pago_Final", "Descripcion",
        "Id_Categoria", "Id_SubCategoria", "Origen", "Origen_Id",
        "Nombre_Categoria", "Nombre_SubCategoria",
    ]
    return _movimiento_to_api(_row_to_item(row, col_names))


def create_movimiento(
    id_usuario: int,
    payload: Dict[str, Any],
    skip_duplicate_check: bool = False,
) -> Dict[str, Any]:
    """
    Crea movimiento. Valida categoría/subcategoría.
    Si Origen y Origen_Id vienen, verifica duplicado (idempotente para ingest).
    """
    fecha = parse_date_flex(payload.get("Fecha") or payload.get("fecha"))
    if not fecha:
        raise ValueError("Fecha es requerida y debe ser YYYY-MM-DD o DD/MM/YYYY")

    monto = parse_money(payload.get("Monto") or payload.get("monto"))
    if monto < 0:
        raise ValueError("Monto debe ser >= 0")

    tipo = str(payload.get("TipoMovimiento") or payload.get("tipo") or "Gasto").strip()
    if tipo.lower() not in ("gasto", "ingreso"):
        tipo = "Gasto"
    tipo = "Ingreso" if tipo.lower() == "ingreso" else "Gasto"

    medio_carga = str(payload.get("MedioCarga") or payload.get("Medio de Carga") or "Manual").strip() or "Manual"
    moneda = str(payload.get("Moneda") or payload.get("moneda") or "ARS").strip() or "ARS"

    id_cat = payload.get("Id_Categoria") or payload.get("idCategoria")
    id_sub = payload.get("Id_SubCategoria") or payload.get("idSubcategoria")
    nombre_cat = str(payload.get("Nombre_Categoria") or "").strip()
    nombre_sub = str(payload.get("Nombre_SubCategoria") or "").strip()

    if id_cat is not None or id_sub is not None:
        if id_cat is not None:
            try:
                id_cat = int(id_cat)
            except (TypeError, ValueError):
                id_cat = None
        if id_sub is not None:
            try:
                id_sub = int(id_sub)
            except (TypeError, ValueError):
                id_sub = None
        id_cat_val, id_sub_val = _validate_categoria_subcategoria(id_usuario, id_cat, id_sub)
    elif nombre_cat or nombre_sub:
        id_cat_val, id_sub_val = _resolve_categoria_subcategoria_from_names(
            id_usuario, nombre_cat or None, nombre_sub or None
        )
    else:
        id_cat_val, id_sub_val = None, None

    # Resolver categoría por ReglaComercio si viene Comercio sin categoría
    comercio = str(payload.get("Comercio") or payload.get("comercio") or "").strip()
    regla_comercio_id: Optional[int] = None
    comercio_raw: Optional[str] = None
    comercio_norm: Optional[str] = None
    if comercio and id_cat_val is None and id_sub_val is None:
        from app.db.regla_comercio import resolve_regla
        from app.utils.normalize import normalize_text
        resolved = resolve_regla(id_usuario, comercio, create_auto_if_no_match=True)
        id_cat_val = resolved.get("id_categoria")
        id_sub_val = resolved.get("id_subcategoria")
        regla_comercio_id = resolved.get("regla_id")
        comercio_raw = comercio[:300] if comercio else None
        comercio_norm = normalize_text(comercio)[:300] if comercio else None

    descripcion = str(payload.get("Descripcion") or payload.get("descripcion") or "").strip() or None
    id_credito = payload.get("Id_Credito_Debito") or payload.get("ID_Credito_Debito")
    id_medio = payload.get("Id_Medio_Pago_Final") or payload.get("ID_Medio_de_pago_final")
    origen = str(payload.get("Origen") or "").strip() or None
    origen_id = str(payload.get("Origen_Id") or "").strip() or None

    if id_credito is not None:
        try:
            id_credito = int(id_credito)
        except (TypeError, ValueError):
            id_credito = None
    if id_medio is not None:
        try:
            id_medio = int(id_medio)
        except (TypeError, ValueError):
            id_medio = None

    # Deduplicación por Origen + Origen_Id
    if not skip_duplicate_check and origen and origen_id:
        existing = get_movimiento_by_origen(id_usuario, origen, origen_id)
        if existing:
            return _movimiento_to_api(existing)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.movimientos
            (Id_usuario, Fecha, MedioCarga, TipoMovimiento, Moneda, Monto,
             Id_Credito_Debito, Id_Medio_Pago_Final, Descripcion,
             Id_Categoria, Id_SubCategoria, Origen, Origen_Id,
             ReglaComercioId, ComercioRaw, ComercioNorm)
            OUTPUT INSERTED.Id, INSERTED.Fecha, INSERTED.[Timestamp], INSERTED.MedioCarga,
                   INSERTED.TipoMovimiento, INSERTED.Moneda, INSERTED.Monto,
                   INSERTED.Id_Credito_Debito, INSERTED.Id_Medio_Pago_Final,
                   INSERTED.Descripcion,
                   INSERTED.Id_Categoria, INSERTED.Id_SubCategoria, INSERTED.Origen, INSERTED.Origen_Id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_usuario,
                fecha,
                medio_carga,
                tipo,
                moneda,
                round(monto, 2),
                id_credito,
                id_medio,
                ((comercio + " " + (descripcion or "")).strip() if comercio else descripcion),
                id_cat_val,
                id_sub_val,
                origen,
                origen_id,
                regla_comercio_id,
                comercio_raw,
                comercio_norm,
            ),
        )
        row = cur.fetchone()
        conn.commit()

    if not row:
        raise RuntimeError("No se pudo crear el movimiento")

    # Re-fetch con JOIN para nombres
    created = get_movimiento(id_usuario, row[0])
    return created or _movimiento_to_api(_row_to_item(row, [
        "Id", "Fecha", "Timestamp", "MedioCarga", "TipoMovimiento", "Moneda", "Monto",
        "Id_Credito_Debito", "Id_Medio_Pago_Final", "Descripcion",
        "Id_Categoria", "Id_SubCategoria", "Origen", "Origen_Id",
    ]))


def get_movimiento_by_origen(id_usuario: int, origen: str, origen_id: str) -> Optional[Dict[str, Any]]:
    """Busca movimiento por Origen + Origen_Id (para deduplicación)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT Id FROM dbo.movimientos
            WHERE Id_usuario = ? AND Origen = ? AND Origen_Id = ?
            """,
            (id_usuario, origen, origen_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return get_movimiento(id_usuario, row[0])


def update_movimiento(
    id_usuario: int,
    mov_id: int,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Actualiza movimiento. Campos editables: Fecha, Monto, Descripcion, Comercio, idCategoria, idSubcategoria, Id_Medio_Pago_Final, Id_Credito_Debito."""
    existing = get_movimiento(id_usuario, mov_id)
    if not existing:
        return None

    updates: List[str] = []
    params: List[Any] = []

    if "Fecha" in payload or "fecha" in payload:
        fecha = parse_date_flex(payload.get("Fecha") or payload.get("fecha"))
        if fecha:
            updates.append("Fecha = ?")
            params.append(fecha)
    if "Monto" in payload or "monto" in payload:
        monto = parse_money(payload.get("Monto") or payload.get("monto"))
        if monto >= 0:
            updates.append("Monto = ?")
            params.append(round(monto, 2))
    if "Descripcion" in payload or "descripcion" in payload:
        updates.append("Descripcion = ?")
        params.append(str(payload.get("Descripcion") or payload.get("descripcion") or "").strip() or None)
    elif "Comercio" in payload or "comercio" in payload:
        updates.append("Descripcion = ?")
        val = str(payload.get("Comercio") or payload.get("comercio") or "").strip()
        params.append(val or None)
    if "idCategoria" in payload or "Id_Categoria" in payload or "Nombre_Categoria" in payload or "Nombre_SubCategoria" in payload:
        id_cat = payload.get("idCategoria") or payload.get("Id_Categoria")
        id_sub = payload.get("idSubcategoria") or payload.get("Id_SubCategoria")
        nombre_cat = str(payload.get("Nombre_Categoria") or "").strip()
        nombre_sub = str(payload.get("Nombre_SubCategoria") or "").strip()
        if id_cat is not None or id_sub is not None:
            id_cat_val, id_sub_val = _validate_categoria_subcategoria(
                id_usuario,
                int(id_cat) if id_cat is not None else None,
                int(id_sub) if id_sub is not None else None,
            )
        elif nombre_cat or nombre_sub:
            id_cat_val, id_sub_val = _resolve_categoria_subcategoria_from_names(
                id_usuario, nombre_cat or None, nombre_sub or None
            )
        else:
            id_cat_val, id_sub_val = None, None
        updates.append("Id_Categoria = ?")
        params.append(id_cat_val)
        updates.append("Id_SubCategoria = ?")
        params.append(id_sub_val)
    if "Id_Medio_Pago_Final" in payload or "ID_Medio_de_pago_final" in payload:
        v = payload.get("Id_Medio_Pago_Final") or payload.get("ID_Medio_de_pago_final")
        updates.append("Id_Medio_Pago_Final = ?")
        params.append(int(v) if v is not None else None)
    if "Id_Credito_Debito" in payload or "ID_Credito_Debito" in payload:
        v = payload.get("Id_Credito_Debito") or payload.get("ID_Credito_Debito")
        updates.append("Id_Credito_Debito = ?")
        params.append(int(v) if v is not None else None)

    if not updates:
        return existing

    updates.append("[Timestamp] = SYSUTCDATETIME()")
    params.extend([id_usuario, mov_id])

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE dbo.movimientos SET {', '.join(updates)} WHERE Id_usuario = ? AND Id = ?",
            params,
        )
        conn.commit()
        if cur.rowcount == 0:
            return None

    return get_movimiento(id_usuario, mov_id)


def recategorize_by_regla(
    id_usuario: int,
    regla_id: int,
    since_date: date,
    id_categoria: int,
    id_subcategoria: int,
) -> int:
    """
    Actualiza movimientos que tienen ReglaComercioId = regla_id y Fecha >= since_date.
    Retorna cantidad de filas actualizadas.
    """
    from app.db.catalog import get_subcategoria_by_id_sql
    sub = get_subcategoria_by_id_sql(id_usuario, id_subcategoria)
    if not sub or int(sub["categoria_id"]) != id_categoria:
        raise ValueError("Subcategoría no pertenece a la categoría o al usuario")

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE m
            SET m.Id_Categoria = ?, m.Id_SubCategoria = ?, m.[Timestamp] = SYSUTCDATETIME()
            FROM dbo.movimientos m
            WHERE m.Id_usuario = ? AND m.Fecha >= ? AND m.ReglaComercioId = ?
            """,
            (id_categoria, id_subcategoria, id_usuario, since_date, regla_id),
        )
        updated = cur.rowcount
        conn.commit()
    return updated


def delete_movimiento(id_usuario: int, mov_id: int) -> bool:
    """Elimina movimiento (hard delete)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM dbo.movimientos WHERE Id_usuario = ? AND Id = ?",
            (id_usuario, mov_id),
        )
        conn.commit()
        return cur.rowcount > 0
