from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import date, datetime, timezone
import re
import time

from app.sheets.client import get_sheets_service
from app.sheets.registry import SHEETS


# =========================
# Helpers base
# =========================

def _values_to_rows(headers: List[str], values: List[List[Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in values:
        obj: Dict[str, Any] = {}
        for i, h in enumerate(headers):
            obj[h] = row[i] if i < len(row) else ""
        out.append(obj)
    return out


def _col_to_a1(col_idx_1based: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA"""
    s = ""
    n = col_idx_1based
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _parse_fecha_ddmmyyyy(value: Any) -> Optional[date]:
    """Parsea DD/MM/YYYY o DD/MM/YYYY HH:MM:SS (ej: 6/02/2026 0:00:00)."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        parts = s.split("/")
        if len(parts) != 3:
            return None
        d, m = int(parts[0]), int(parts[1])
        y_str = parts[2].split()[0] if parts[2] else ""
        y = int(y_str) if y_str else 0
        if not y:
            return None
        return date(y, m, d)
    except Exception:
        return None


def _parse_monto(value: Any) -> float:
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0

    # tu caso: "48,146" -> 48146
    s = s.replace(",", "")
    s = re.sub(r"[^0-9\.\-]", "", s)

    try:
        return float(s) if s else 0.0
    except Exception:
        return 0.0


def _now_timestamp_iso_local() -> str:
    # ISO con offset (similar a tu ejemplo). astimezone() agrega el -03:00 local.
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


# =========================
# Lectura (ya la tenías)
# =========================

def read_table(entity: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    cfg = SHEETS[entity]
    svc = get_sheets_service()

    header_range = f"{cfg.worksheet}!A{cfg.header_row}:Z{cfg.header_row}"
    header_resp = svc.spreadsheets().values().get(
        spreadsheetId=cfg.spreadsheet_id,
        range=header_range,
    ).execute()
    headers = header_resp.get("values", [[]])[0]
    if not headers:
        return [], []

    data_range = f"{cfg.worksheet}!A{cfg.header_row + 1}:Z"
    data_resp = svc.spreadsheets().values().get(
        spreadsheetId=cfg.spreadsheet_id,
        range=data_range,
    ).execute()
    values = data_resp.get("values", [])

    rows = _values_to_rows(headers, values)
    return headers, rows


def _movimiento_to_item(r: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza row de Sheets a formato API (snake_case, fecha YYYY-MM-DD)."""
    r_fecha = _parse_fecha_ddmmyyyy(r.get("Fecha"))
    if not r_fecha:
        r_fecha = _parse_fecha_ddmmyyyy(r.get("Timestamp"))
    fecha_str = r_fecha.strftime("%Y-%m-%d") if r_fecha else ""
    tipo_raw = str(r.get("Tipo de Movimiento", "")).strip().lower()
    tipo = "Ingreso" if tipo_raw == "ingreso" else "Gasto"
    return {
        "id": str(r.get("Id", "")).strip(),
        "fecha": fecha_str,
        "timestamp": str(r.get("Timestamp", "")).strip(),
        "tipo": tipo,
        "moneda": str(r.get("Moneda", "")).strip(),
        "monto": round(_parse_monto(r.get("Monto")), 2),
        "comercio": str(r.get("Comercio", "")).strip(),
        "descripcion": str(r.get("Descripcion", "")).strip(),
        "categoria": str(r.get("Nombre_Categoria", "")).strip(),
        "subcategoria": str(r.get("Nombre_SubCategoria", "")).strip(),
        "medio_pago": str(r.get("Medios de pago", "")).strip(),
    }


def list_movimientos(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    tipo: Optional[str] = None,
    categoria: Optional[str] = None,
    subcategoria: Optional[str] = None,
    comercio: Optional[str] = None,
    moneda: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "fecha_desc",
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    q: Optional[str] = None,
    categoria_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _, rows = read_table("movimientos")

    if categoria_id and not categoria:
        from app.sheets.catalog_service import list_categorias
        cats = list_categorias()
        for c in cats:
            if str(c.get("id", "")).strip() == str(categoria_id).strip():
                categoria = c.get("nombre", "")
                break

    filtered: List[Dict[str, Any]] = []

    for r in rows:
        r_fecha = _parse_fecha_ddmmyyyy(r.get("Fecha"))

        if from_date and r_fecha and r_fecha < from_date:
            continue
        if to_date and r_fecha and r_fecha > to_date:
            continue

        if tipo:
            val = str(r.get("Tipo de Movimiento", "")).strip().lower()
            if val != tipo.strip().lower():
                continue

        if categoria and str(r.get("Nombre_Categoria", "")).strip().lower() != categoria.strip().lower():
            continue
        if subcategoria and str(r.get("Nombre_SubCategoria", "")).strip().lower() != subcategoria.strip().lower():
            continue

        if comercio and comercio.strip().lower() not in str(r.get("Comercio", "")).strip().lower():
            continue

        if moneda and str(r.get("Moneda", "")).strip().upper() != moneda.strip().upper():
            continue

        # Cada usuario tiene su propio spreadsheet (ID_Sheets). El spreadsheet es el límite
        # por usuario; no filtrar por Id_usuario (evita excluir filas con columna vacía).
        monto = _parse_monto(r.get("Monto"))
        if min_amount is not None and monto < min_amount:
            continue
        if max_amount is not None and monto > max_amount:
            continue

        if q:
            q_lower = q.strip().lower()
            comercio_s = str(r.get("Comercio", "")).strip().lower()
            desc_s = str(r.get("Descripcion", "")).strip().lower()
            if q_lower not in comercio_s and q_lower not in desc_s:
                continue

        filtered.append(r)

    def key_fecha_parsed(x: Dict[str, Any]) -> date:
        return _parse_fecha_ddmmyyyy(x.get("Fecha")) or date.min

    def key_monto(x: Dict[str, Any]) -> float:
        return _parse_monto(x.get("Monto"))

    def key_timestamp(x: Dict[str, Any]) -> str:
        return str(x.get("Timestamp", "")).strip()

    if sort == "fecha_asc":
        filtered.sort(key=key_fecha_parsed)
    elif sort == "fecha_desc":
        filtered.sort(key=key_fecha_parsed, reverse=True)
    elif sort == "monto_asc":
        filtered.sort(key=key_monto)
    elif sort == "monto_desc":
        filtered.sort(key=key_monto, reverse=True)
    elif sort == "timestamp_desc":
        filtered.sort(key=key_timestamp, reverse=True)
    elif sort == "timestamp_asc":
        filtered.sort(key=key_timestamp)
    else:
        filtered.sort(key=key_fecha_parsed, reverse=True)

    return filtered[offset: offset + limit]


def list_movimientos_paginated(
    period: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    tipo: str = "Gasto",
    categoria: Optional[str] = None,
    subcategoria: Optional[str] = None,
    comercio: Optional[str] = None,
    moneda: Optional[str] = None,
    user_id: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    q: Optional[str] = None,
    categoria_id: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    sort: str = "timestamp_desc",
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retorna (items_normalizados, total) para respuesta paginada.
    Si period viene, deriva from_date y to_date.
    """
    if period:
        from app.utils.parse_utils import parse_period
        try:
            fd, td = parse_period(period)
            from_date = fd
            to_date = td
        except ValueError:
            pass

    tipo_norm = (tipo or "Gasto").strip().lower()
    if tipo_norm != "ingreso":
        tipo_norm = "gasto"

    offset = (page - 1) * limit if page > 0 else 0
    all_rows = list_movimientos(
        from_date=from_date,
        to_date=to_date,
        tipo=tipo_norm,
        categoria=categoria,
        subcategoria=subcategoria,
        comercio=comercio,
        moneda=moneda,
        user_id=user_id,
        limit=999999,
        offset=0,
        sort=sort,
        min_amount=min_amount,
        max_amount=max_amount,
        q=q,
        categoria_id=categoria_id,
    )
    total = len(all_rows)
    rows = all_rows[offset: offset + limit]
    items = [_movimiento_to_item(r) for r in rows]
    return items, total


def get_movimiento_by_id(mov_id: str) -> Optional[Dict[str, Any]]:
    cfg = SHEETS["movimientos"]
    _, rows = read_table("movimientos")
    for r in rows:
        if str(r.get(cfg.id_column, "")).strip() == str(mov_id).strip():
            return r
    return None


# =========================
# Escritura: POST (append + lookup por Timestamp)
# =========================

def _get_headers_and_values_raw(entity: str) -> Tuple[List[str], List[List[Any]]]:
    """Devuelve headers y values raw (listas) para poder ubicar filas/índices."""
    cfg = SHEETS[entity]
    svc = get_sheets_service()

    header_range = f"{cfg.worksheet}!A{cfg.header_row}:Z{cfg.header_row}"
    header_resp = svc.spreadsheets().values().get(
        spreadsheetId=cfg.spreadsheet_id,
        range=header_range,
    ).execute()
    headers = header_resp.get("values", [[]])[0]
    if not headers:
        return [], []

    data_range = f"{cfg.worksheet}!A{cfg.header_row + 1}:Z"
    data_resp = svc.spreadsheets().values().get(
        spreadsheetId=cfg.spreadsheet_id,
        range=data_range,
    ).execute()
    values = data_resp.get("values", [])

    return headers, values


def _find_row_index_by_column_value(
    headers: List[str],
    values: List[List[Any]],
    column_name: str,
    needle: str,
) -> Optional[int]:
    """Retorna índice 0-based dentro de values (no el número de fila en Sheets)."""
    try:
        col_idx = headers.index(column_name)
    except ValueError:
        return None

    needle_s = str(needle).strip()
    for i, row in enumerate(values):
        cell = row[col_idx] if col_idx < len(row) else ""
        if str(cell).strip() == needle_s:
            return i
    return None


def create_movimiento(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una fila en Movimientos.
    - No recibe Id (porque lo genera el Sheet).
    - Setea Timestamp ISO único.
    - Hace lookup por Timestamp para recuperar el Id generado y devolver el registro completo.
    """
    cfg = SHEETS["movimientos"]
    svc = get_sheets_service()

    headers, _ = _get_headers_and_values_raw("movimientos")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Movimientos")

    # Timestamp correlación
    ts = _now_timestamp_iso_local()

    # Armamos la fila respetando orden de headers.
    # Id lo dejamos vacío; Timestamp lo seteamos.
    row_out: List[Any] = []
    for h in headers:
        if h == cfg.id_column:
            row_out.append("")  # Id generado por Sheet
        elif h == "Timestamp":
            row_out.append(ts)
        else:
            row_out.append(payload.get(h, ""))

    # Append
    append_range = f"{cfg.worksheet}!A{cfg.header_row + 1}:Z"
    svc.spreadsheets().values().append(
        spreadsheetId=cfg.spreadsheet_id,
        range=append_range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_out]},
    ).execute()

    # Pequeña espera para que se calculen fórmulas/Id si aplica
    time.sleep(0.2)

    # Lookup por Timestamp para recuperar fila real (con Id ya calculado)
    headers2, values2 = _get_headers_and_values_raw("movimientos")
    idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        # fallback: reintento corto
        time.sleep(0.3)
        headers2, values2 = _get_headers_and_values_raw("movimientos")
        idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)

    if idx is None:
        raise RuntimeError("Insert OK pero no pude re-encontrar la fila por Timestamp")

    row_dict = _values_to_rows(headers2, [values2[idx]])[0]
    return row_dict


# =========================
# Escritura: PATCH por Id
# =========================

def patch_movimiento_by_id(mov_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza solo columnas presentes en patch, encontrando la fila por Id.
    """
    cfg = SHEETS["movimientos"]
    svc = get_sheets_service()

    headers, values = _get_headers_and_values_raw("movimientos")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Movimientos")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, mov_id)
    if idx is None:
        raise KeyError("Movimiento no encontrado")

    # Número de fila real en Sheets:
    # header_row = 1, data empieza en header_row+1, idx es 0-based en values
    row_number = cfg.header_row + 1 + idx

    # Armamos actualizaciones por celdas (una por columna). Simple y claro.
    updates = []
    for col_name, new_value in patch.items():
        if col_name not in headers:
            continue
        if col_name == cfg.id_column:
            continue  # no se cambia Id
        col_letter = _col_to_a1(headers.index(col_name) + 1)
        a1 = f"{cfg.worksheet}!{col_letter}{row_number}"
        updates.append({"range": a1, "values": [[new_value]]})

    if updates:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=cfg.spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": updates},
        ).execute()

    # Devolvemos el registro actualizado (re-lectura por Id)
    updated = get_movimiento_by_id(mov_id)
    if not updated:
        raise RuntimeError("Actualicé pero luego no pude leer el movimiento")
    return updated
