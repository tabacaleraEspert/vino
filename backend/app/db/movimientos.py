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


def _resolve_comercio_id(comercio_raw: Optional[str], id_usuario: Optional[int] = None) -> Optional[str]:
    """Resuelve nombre de comercio a id (ReglaComercio.Id). Retorna None si no hay comercio asociado."""
    if not comercio_raw or not str(comercio_raw).strip():
        return None
    name = str(comercio_raw).strip()
    if id_usuario is not None:
        try:
            from app.db.comercios import get_comercio_id_by_name_sql
            cid = get_comercio_id_by_name_sql(id_usuario, name)
            if cid:
                return cid
        except Exception:
            pass
    return None


def _movimiento_to_api(
    row: Dict[str, Any],
    id_usuario: Optional[int] = None,
    comercio_id_cache: Optional[Dict[str, str]] = None,
    regla_cat_cache: Optional[Dict[str, tuple[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Formato compatible con frontend (MovimientoItem / MovimientoRaw).
    comercio_id_cache: {PatronNorm: id} para evitar N+1 en listados.
    regla_cat_cache: {regla_id: (nombre_categoria, nombre_subcategoria)} para enriquecer categoría
      cuando el SQL no la devuelve pero el movimiento tiene comercio asociado.
    """
    fecha = row.get("Fecha")
    if isinstance(fecha, date):
        fecha = fecha.strftime("%Y-%m-%d")
    tipo_raw = str(row.get("TipoMovimiento", "")).strip().lower()
    tipo = "Ingreso" if tipo_raw == "ingreso" else "Gasto"
    monto = row.get("Monto")
    if monto is not None:
        monto = round(float(monto), 2)

    comercio_raw = str(row.get("ComercioRaw", "") or "").strip()
    descripcion = str(row.get("Descripcion", "") or "").strip()
    comercio_str = comercio_raw or descripcion
    comercio_id = row.get("ComercioId")
    if not comercio_id and (comercio_raw or descripcion):
        if comercio_id_cache is not None:
            from app.utils.normalize import normalize_text
            key = normalize_text(comercio_raw or descripcion)
            comercio_id = comercio_id_cache.get(key) if key else None
        if not comercio_id and id_usuario is not None:
            comercio_id = _resolve_comercio_id(comercio_raw or descripcion, id_usuario)

    id_cat = row.get("Id_Categoria_Efectivo") or row.get("Id_Categoria")
    id_sub = row.get("Id_SubCategoria_Efectivo") or row.get("Id_SubCategoria")
    nom_cat = str(row.get("Nombre_Categoria", "") or "").strip()
    nom_sub = str(row.get("Nombre_SubCategoria", "") or "").strip()

    # Fallback: si categoría vacía pero hay comercio asociado, usar la de la regla (igual que Gastos)
    if (not nom_cat or nom_cat.lower() == "sin categoría") and comercio_id and regla_cat_cache:
        cid = str(comercio_id).strip()
        if cid.isdigit() and cid in regla_cat_cache:
            cat_sub = regla_cat_cache[cid]
            if cat_sub and cat_sub[0]:
                nom_cat = cat_sub[0]
                nom_sub = cat_sub[1] or nom_sub

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
        "comercio": comercio_str,
        "Comercio": comercio_str,
        "comercioId": comercio_id,
        "descripcion": descripcion,
        "Descripcion": descripcion,
        "categoria": nom_cat,
        "Nombre_Categoria": nom_cat,
        "subcategoria": nom_sub,
        "Nombre_SubCategoria": nom_sub,
        "medio_pago": str(row.get("Id_Medio_Pago_Final", "") or ""),
        "idCategoria": str(id_cat) if id_cat else None,
        "idSubcategoria": str(id_sub) if id_sub else None,
        "Id_Categoria": id_cat,
        "Id_SubCategoria": id_sub,
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
        moneda_norm = moneda.strip().upper()
        # Incluir Moneda vacía/NULL cuando se filtra por ARS (compatibilidad con datos legacy)
        if moneda_norm == "ARS":
            conditions.append("(m.Moneda = ? OR LTRIM(RTRIM(ISNULL(m.Moneda, ''))) = '')")
        else:
            conditions.append("m.Moneda = ?")
        params.append(moneda_norm)
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

    col_names = [
        "Id", "Fecha", "Timestamp", "MedioCarga", "TipoMovimiento", "Moneda", "Monto",
        "Id_Credito_Debito", "Id_Medio_Pago_Final", "Descripcion",
        "Id_Categoria", "Id_SubCategoria", "Origen", "Origen_Id",
        "ComercioRaw", "ComercioId", "CategoriaManual", "ReglaComercioId",
        "Id_Categoria_Efectivo", "Id_SubCategoria_Efectivo",
        "Nombre_Categoria", "Nombre_SubCategoria", "_total",
    ]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT * FROM (
                SELECT
                  m.Id, m.Fecha, m.[Timestamp], m.MedioCarga, m.TipoMovimiento, m.Moneda, m.Monto,
                  m.Id_Credito_Debito, m.Id_Medio_Pago_Final, m.Descripcion,
                  m.Id_Categoria, m.Id_SubCategoria, m.Origen, m.Origen_Id,
                  m.ComercioRaw, m.ComercioId,
                  ISNULL(m.CategoriaManual, 0) AS CategoriaManual,
                  m.ReglaComercioId,
                  COALESCE(CASE WHEN ISNULL(m.CategoriaManual, 0) = 1 THEN m.Id_Categoria ELSE rc.Id_Categoria END, m.Id_Categoria) AS Id_Categoria_Efectivo,
                  COALESCE(CASE WHEN ISNULL(m.CategoriaManual, 0) = 1 THEN m.Id_SubCategoria ELSE rc.Id_SubCategoria END, m.Id_SubCategoria) AS Id_SubCategoria_Efectivo,
                  c.Nombre AS Nombre_Categoria,
                  sc.Nombre_SubCategoria,
                  COUNT(*) OVER() AS _total
                FROM dbo.movimientos m
                LEFT JOIN dbo.ReglaComercio rc ON rc.Id = COALESCE(m.ReglaComercioId, TRY_CAST(m.ComercioId AS INT)) AND rc.Id_usuario = m.Id_usuario
                LEFT JOIN dbo.Categoria c ON c.Id = COALESCE(CASE WHEN ISNULL(m.CategoriaManual, 0) = 1 THEN m.Id_Categoria ELSE rc.Id_Categoria END, m.Id_Categoria) AND c.Id_usuario = m.Id_usuario
                LEFT JOIN dbo.SubCategoria sc ON sc.Id = COALESCE(CASE WHEN ISNULL(m.CategoriaManual, 0) = 1 THEN m.Id_SubCategoria ELSE rc.Id_SubCategoria END, m.Id_SubCategoria) AND sc.Id_usuario = m.Id_usuario
                WHERE {where}
            ) AS sub
            ORDER BY sub.Fecha DESC, sub.Id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """,
            params + [offset, limit],
        )
        rows = cur.fetchall()

        # Pre-resolver comercio_id en la misma conexión (evitar N+1 y agotar pool)
        comercio_id_cache: Dict[str, str] = {}
        if rows and id_usuario is not None:
            from app.utils.normalize import normalize_text
            seen: set = set()
            patron_norms: List[str] = []
            for r in rows:
                row_dict = _row_to_item(tuple(r[:-1]), col_names[:-1])
                if not row_dict.get("ComercioId"):
                    raw = str(row_dict.get("ComercioRaw", "") or "").strip()
                    desc = str(row_dict.get("Descripcion", "") or "").strip()
                    n = raw or desc
                    if n:
                        pn = normalize_text(n)
                        if pn and pn not in seen:
                            patron_norms.append(pn)
                            seen.add(pn)
            if patron_norms:
                ph = ",".join("?" * len(patron_norms))
                cur.execute(
                    f"""
                    SELECT Id, PatronNorm FROM dbo.ReglaComercio
                    WHERE Id_usuario = ? AND PatronNorm IN ({ph})
                    """,
                    [id_usuario] + patron_norms,
                )
                for r in cur.fetchall():
                    comercio_id_cache[str(r[1]).strip()] = str(r[0])

        # Cache categoría por regla (para enriquecer cuando SQL no devuelve cat pero hay comercio)
        regla_cat_cache: Dict[str, tuple[str, str]] = {}
        if rows and id_usuario is not None:
            regla_ids: set = set(comercio_id_cache.values()) if comercio_id_cache else set()
            for r in rows:
                row_dict = _row_to_item(tuple(r[:-1]), col_names[:-1])
                cid = row_dict.get("ComercioId")
                rid = row_dict.get("ReglaComercioId")
                if cid and str(cid).strip().isdigit():
                    regla_ids.add(str(cid).strip())
                if rid is not None:
                    regla_ids.add(str(rid))
            numeric_ids = [int(x) for x in regla_ids if str(x).strip().isdigit()]
            if numeric_ids:
                placeholders = ",".join("?" * len(numeric_ids))
                cur.execute(
                    f"""
                    SELECT rc.Id, c.Nombre, sc.Nombre_SubCategoria
                    FROM dbo.ReglaComercio rc
                    JOIN dbo.Categoria c ON c.Id = rc.Id_Categoria AND c.Id_usuario = rc.Id_usuario
                    JOIN dbo.SubCategoria sc ON sc.Id = rc.Id_SubCategoria AND sc.Id_usuario = rc.Id_usuario
                    WHERE rc.Id_usuario = ? AND rc.Id IN ({placeholders})
                    """,
                    [id_usuario] + numeric_ids,
                )
                for r in cur.fetchall():
                    regla_cat_cache[str(r[0])] = (str(r[1] or "").strip(), str(r[2] or "").strip())

    total = int(rows[0][-1]) if rows else 0
    # Quitar _total del row antes de mapear (no va en el item)
    items = [
        _movimiento_to_api(
            _row_to_item(tuple(r[:-1]), col_names[:-1]),
            id_usuario,
            comercio_id_cache,
            regla_cat_cache if rows and id_usuario else None,
        )
        for r in rows
    ]
    return items, total


def list_comercios_from_movimientos(id_usuario: int, limit: int = 500) -> List[str]:
    """Lista nombres únicos de comercio (Descripcion) de los movimientos del usuario."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT LTRIM(RTRIM(m.Descripcion))
            FROM dbo.movimientos m
            WHERE m.Id_usuario = ? AND m.Descripcion IS NOT NULL AND LTRIM(RTRIM(m.Descripcion)) != ''
            ORDER BY 1
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """,
            (id_usuario, limit),
        )
        rows = cur.fetchall()
    return [str(r[0]).strip() for r in rows if r[0]]


def get_movimiento(id_usuario: int, mov_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un movimiento por Id."""
    col_names = [
        "Id", "Fecha", "Timestamp", "MedioCarga", "TipoMovimiento", "Moneda", "Monto",
        "Id_Credito_Debito", "Id_Medio_Pago_Final", "Descripcion",
        "Id_Categoria", "Id_SubCategoria", "Origen", "Origen_Id",
        "ComercioRaw", "ComercioId", "CategoriaManual", "ReglaComercioId",
        "Id_Categoria_Efectivo", "Id_SubCategoria_Efectivo",
        "Nombre_Categoria", "Nombre_SubCategoria",
    ]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              m.Id, m.Fecha, m.[Timestamp], m.MedioCarga, m.TipoMovimiento, m.Moneda, m.Monto,
              m.Id_Credito_Debito, m.Id_Medio_Pago_Final, m.Descripcion,
              m.Id_Categoria, m.Id_SubCategoria, m.Origen, m.Origen_Id,
              m.ComercioRaw, m.ComercioId,
              ISNULL(m.CategoriaManual, 0) AS CategoriaManual,
              m.ReglaComercioId,
              COALESCE(CASE WHEN ISNULL(m.CategoriaManual, 0) = 1 THEN m.Id_Categoria ELSE rc.Id_Categoria END, m.Id_Categoria) AS Id_Categoria_Efectivo,
              COALESCE(CASE WHEN ISNULL(m.CategoriaManual, 0) = 1 THEN m.Id_SubCategoria ELSE rc.Id_SubCategoria END, m.Id_SubCategoria) AS Id_SubCategoria_Efectivo,
              c.Nombre AS Nombre_Categoria,
              sc.Nombre_SubCategoria
            FROM dbo.movimientos m
            LEFT JOIN dbo.ReglaComercio rc ON rc.Id = COALESCE(m.ReglaComercioId, TRY_CAST(m.ComercioId AS INT)) AND rc.Id_usuario = m.Id_usuario
            LEFT JOIN dbo.Categoria c ON c.Id = COALESCE(CASE WHEN ISNULL(m.CategoriaManual, 0) = 1 THEN m.Id_Categoria ELSE rc.Id_Categoria END, m.Id_Categoria) AND c.Id_usuario = m.Id_usuario
            LEFT JOIN dbo.SubCategoria sc ON sc.Id = COALESCE(CASE WHEN ISNULL(m.CategoriaManual, 0) = 1 THEN m.Id_SubCategoria ELSE rc.Id_SubCategoria END, m.Id_SubCategoria) AND sc.Id_usuario = m.Id_usuario
            WHERE m.Id_usuario = ? AND m.Id = ?
            """,
            (id_usuario, mov_id),
        )
        row = cur.fetchone()

    if not row:
        return None
    row_dict = _row_to_item(row, col_names)
    # Resolver comercio_id si no está (igual que en list_movimientos)
    if not row_dict.get("ComercioId"):
        raw = str(row_dict.get("ComercioRaw", "") or "").strip()
        desc = str(row_dict.get("Descripcion", "") or "").strip()
        cid_resolved = _resolve_comercio_id(raw or desc, id_usuario)
        if cid_resolved:
            row_dict["ComercioId"] = cid_resolved
    regla_cat_cache: Optional[Dict[str, tuple[str, str]]] = None
    cid = row_dict.get("ComercioId") or row_dict.get("ReglaComercioId")
    if cid and str(cid).strip().isdigit():
        from app.db.regla_comercio import get_regla_by_id
        regla = get_regla_by_id(id_usuario, cid)
        if regla:
            regla_cat_cache = {
                str(cid): (
                    str(regla.get("nombreCategoria", "") or "").strip(),
                    str(regla.get("nombreSubcategoria", "") or "").strip(),
                )
            }
    return _movimiento_to_api(row_dict, id_usuario, None, regla_cat_cache)


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
            return existing

    user_provided_cat = bool(
        payload.get("Id_Categoria") or payload.get("idCategoria")
        or payload.get("Nombre_Categoria") or payload.get("Nombre_SubCategoria")
    )
    categoria_manual = 1 if user_provided_cat else 0
    comercio_id = _resolve_comercio_id(comercio_raw or comercio, id_usuario)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.movimientos
            (Id_usuario, Fecha, MedioCarga, TipoMovimiento, Moneda, Monto,
             Id_Credito_Debito, Id_Medio_Pago_Final, Descripcion,
             Id_Categoria, Id_SubCategoria, Origen, Origen_Id,
             ReglaComercioId, ComercioRaw, ComercioNorm, ComercioId, CategoriaManual)
            OUTPUT INSERTED.Id, INSERTED.Fecha, INSERTED.[Timestamp], INSERTED.MedioCarga,
                   INSERTED.TipoMovimiento, INSERTED.Moneda, INSERTED.Monto,
                   INSERTED.Id_Credito_Debito, INSERTED.Id_Medio_Pago_Final,
                   INSERTED.Descripcion,
                   INSERTED.Id_Categoria, INSERTED.Id_SubCategoria, INSERTED.Origen, INSERTED.Origen_Id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                comercio_id,
                categoria_manual,
            ),
        )
        row = cur.fetchone()
        conn.commit()

    if not row:
        raise RuntimeError("No se pudo crear el movimiento")

    # Re-fetch con JOIN para nombres
    created = get_movimiento(id_usuario, row[0])
    if created:
        return created
    # Fallback si get_movimiento falla (ej. tabla sin ComercioId)
    row_dict = _row_to_item(row, [
        "Id", "Fecha", "Timestamp", "MedioCarga", "TipoMovimiento", "Moneda", "Monto",
        "Id_Credito_Debito", "Id_Medio_Pago_Final", "Descripcion",
        "Id_Categoria", "Id_SubCategoria", "Origen", "Origen_Id",
    ])
    return _movimiento_to_api(row_dict, id_usuario)


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
        updates.append("CategoriaManual = 1")
    if "comercioId" in payload or "ComercioId" in payload:
        # Asociar comercio por id (desde dropdown)
        comercio_id = str(payload.get("comercioId") or payload.get("ComercioId") or "").strip()
        if comercio_id:
            from app.db.comercios import get_comercio_by_id_sql
            comercio = get_comercio_by_id_sql(id_usuario, comercio_id)
            if comercio:
                updates.append("ComercioId = ?")
                params.append(comercio_id)
                updates.append("ReglaComercioId = ?")
                params.append(int(comercio_id))
                nombre = (comercio.get("name") or "").strip()
                updates.append("ComercioRaw = ?")
                params.append(nombre[:300] if nombre else None)
                from app.utils.normalize import normalize_text
                updates.append("ComercioNorm = ?")
                params.append(normalize_text(nombre)[:300] if nombre else None)
                # Si no se asignó cat/subcat explícitamente, usar las del comercio
                if "idCategoria" not in payload and "Id_Categoria" not in payload and "Nombre_Categoria" not in payload:
                    id_cat_comercio = comercio.get("defaultCategoryId")
                    id_sub_comercio = comercio.get("defaultSubcategoryId")
                    if id_cat_comercio or id_sub_comercio:
                        try:
                            id_cat_val = int(id_cat_comercio) if id_cat_comercio else None
                            id_sub_val = int(id_sub_comercio) if id_sub_comercio else None
                            id_cat_val, id_sub_val = _validate_categoria_subcategoria(id_usuario, id_cat_val, id_sub_val)
                            updates.append("Id_Categoria = ?")
                            params.append(id_cat_val)
                            updates.append("Id_SubCategoria = ?")
                            params.append(id_sub_val)
                            updates.append("CategoriaManual = 0")
                        except (ValueError, TypeError):
                            pass
        else:
            # Desasociar comercio
            updates.append("ComercioId = ?")
            params.append(None)
            updates.append("ReglaComercioId = ?")
            params.append(None)
    elif "Comercio" in payload or "comercio" in payload:
        comercio_val = str(payload.get("Comercio") or payload.get("comercio") or "").strip()
        comercio_id = _resolve_comercio_id(comercio_val, id_usuario)
        updates.append("ComercioId = ?")
        params.append(comercio_id)
        updates.append("ComercioRaw = ?")
        params.append(comercio_val[:300] if comercio_val else None)
        from app.utils.normalize import normalize_text
        updates.append("ComercioNorm = ?")
        params.append(normalize_text(comercio_val)[:300] if comercio_val else None)
        if comercio_id and str(comercio_id).isdigit():
            updates.append("ReglaComercioId = ?")
            params.append(int(comercio_id))
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
