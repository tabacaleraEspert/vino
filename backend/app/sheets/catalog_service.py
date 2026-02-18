from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from app.cache.sheets_cache import invalidate
from app.sheets.client import get_sheets_service
from app.sheets.registry import SHEETS, get_current_spreadsheet_id
from app.sheets.service import (
    _col_to_a1,
    _find_row_index_by_column_value,
    _get_headers_and_values_raw,
    _now_timestamp_iso_local,
    _values_to_rows,
    patch_movimiento_by_id,
    read_table,
)

# Defaults para categorías sin icon/color en Sheets
DEFAULT_ICON = "📁"
DEFAULT_COLOR = "#6b7280"


def list_categorias() -> List[Dict[str, Any]]:
    _, rows = read_table("categorias")
    # headers: Id, Nombre, [Icon], [Color]
    out = []
    for r in rows:
        if not str(r.get("Id", "")).strip():
            continue
        nombre = str(r.get("Nombre", "")).strip()
        icon = str(r.get("Icon", "")).strip() or DEFAULT_ICON
        color = str(r.get("Color", "")).strip() or DEFAULT_COLOR
        out.append({
            "id": str(r.get("Id", "")).strip(),
            "nombre": nombre,
            "icon": icon,
            "color": color,
        })
    out.sort(key=lambda x: x["nombre"].lower())
    return out


def create_categoria(nombre: str, icon: str = DEFAULT_ICON, color: str = DEFAULT_COLOR) -> Dict[str, Any]:
    """
    Crea una categoría en Sheets.
    La hoja Categoria debe tener: Id, Nombre, Icon, Color, Timestamp.
    Agregar columnas Icon, Color, Timestamp si no existen.
    """
    cfg = SHEETS["categorias"]
    svc = get_sheets_service()
    headers, _ = _get_headers_and_values_raw("categorias")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Categoria")
    if "Timestamp" not in headers:
        raise RuntimeError(
            "La hoja Categoria necesita columna 'Timestamp'. "
            "Agregá las columnas: Icon, Color, Timestamp."
        )

    ts = _now_timestamp_iso_local()
    row_out: List[Any] = []
    for h in headers:
        if h == cfg.id_column:
            row_out.append("")
        elif h == "Timestamp":
            row_out.append(ts)
        elif h == "Nombre":
            row_out.append(nombre)
        elif h == "Icon":
            row_out.append(icon)
        elif h == "Color":
            row_out.append(color)
        else:
            row_out.append("")

    append_range = f"{cfg.worksheet}!A{cfg.header_row + 1}:Z"
    svc.spreadsheets().values().append(
        spreadsheetId=cfg.spreadsheet_id,
        range=append_range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_out]},
    ).execute()

    time.sleep(0.2)
    headers2, values2 = _get_headers_and_values_raw("categorias")
    idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        time.sleep(0.3)
        headers2, values2 = _get_headers_and_values_raw("categorias")
        idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        raise RuntimeError("Insert OK pero no pude re-encontrar la fila por Timestamp")

    row_dict = _values_to_rows(headers2, [values2[idx]])[0]
    invalidate(get_current_spreadsheet_id(), "categorias")
    r = _categoria_row_to_response(row_dict)
    r["name"] = r["nombre"]
    return r


def patch_categoria_by_id(cat_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza categoría por Id. No permite cambiar Id."""
    cfg = SHEETS["categorias"]
    svc = get_sheets_service()
    headers, values = _get_headers_and_values_raw("categorias")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Categoria")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, cat_id)
    if idx is None:
        raise KeyError("Categoría no encontrada")

    row_number = cfg.header_row + 1 + idx
    # Frontend envía name/icon/color (camelCase)
    api_to_sheet = {"name": "Nombre", "nombre": "Nombre", "icon": "Icon", "color": "Color"}
    updates = []
    for api_key, col_name in api_to_sheet.items():
        if api_key not in patch or col_name not in headers:
            continue
        col_letter = _col_to_a1(headers.index(col_name) + 1)
        a1 = f"{cfg.worksheet}!{col_letter}{row_number}"
        updates.append({"range": a1, "values": [[patch[api_key]]]})

    if updates:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=cfg.spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": updates},
        ).execute()
        invalidate(get_current_spreadsheet_id(), "categorias")

    updated = get_categoria_by_id(cat_id)
    if not updated:
        raise RuntimeError("Actualicé pero no pude leer la categoría")
    updated["name"] = updated["nombre"]
    return updated


def get_categoria_by_id(cat_id: str) -> Optional[Dict[str, Any]]:
    _, rows = read_table("categorias")
    for r in rows:
        if str(r.get("Id", "")).strip() == str(cat_id).strip():
            return _categoria_row_to_response(r)
    return None


def _categoria_row_to_response(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row.get("Id", "")).strip(),
        "nombre": str(row.get("Nombre", "")).strip(),
        "icon": str(row.get("Icon", "")).strip() or DEFAULT_ICON,
        "color": str(row.get("Color", "")).strip() or DEFAULT_COLOR,
    }


def delete_categoria_by_id(cat_id: str) -> bool:
    """Elimina la fila de la categoría en Sheets."""
    cfg = SHEETS["categorias"]
    svc = get_sheets_service()
    headers, values = _get_headers_and_values_raw("categorias")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Categoria")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, cat_id)
    if idx is None:
        return False

    spreadsheet = svc.spreadsheets().get(spreadsheetId=cfg.spreadsheet_id).execute()
    sheet_id = None
    for s in spreadsheet.get("sheets", []):
        if s.get("properties", {}).get("title") == cfg.worksheet:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        raise RuntimeError("No se encontró la hoja Categoria")

    row_number = cfg.header_row + 1 + idx
    svc.spreadsheets().batchUpdate(
        spreadsheetId=cfg.spreadsheet_id,
        body={
            "requests": [{
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_number - 1,
                        "endIndex": row_number,
                    }
                }
            }]
        },
    ).execute()
    invalidate(get_current_spreadsheet_id(), "categorias")
    return True


def create_subcategoria(categoria_id: str, nombre: str) -> Dict[str, Any]:
    """
    Crea una subcategoría en Sheets asociada a la categoría.
    Chequeos: categoría existe, nombre no duplicado en la misma categoría.
    La hoja Sub-Categoria debe tener: Id_Categoria, Id, Nombre_SubCategoria, Timestamp.
    """
    if not get_categoria_by_id(categoria_id):
        raise KeyError("Categoría no encontrada")
    subs = list_subcategorias(categoria_id=categoria_id)
    nombre_norm = nombre.strip().lower()
    for s in subs:
        if s.get("nombre", "").strip().lower() == nombre_norm:
            raise ValueError(
                f"Ya existe una subcategoría llamada '{nombre.strip()}' en esta categoría"
            )
    cfg = SHEETS["subcategorias"]
    svc = get_sheets_service()
    headers, _ = _get_headers_and_values_raw("subcategorias")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Sub-Categoria")
    if "Timestamp" not in headers:
        raise RuntimeError(
            "La hoja Sub-Categoria necesita columna 'Timestamp'. "
            "Agregá la columna Timestamp."
        )

    ts = _now_timestamp_iso_local()
    row_out: List[Any] = []
    for h in headers:
        if h == "Id_Categoria":
            row_out.append(categoria_id)
        elif h == cfg.id_column:
            row_out.append("")
        elif h == "Nombre_SubCategoria":
            row_out.append(nombre)
        elif h == "Timestamp":
            row_out.append(ts)
        else:
            row_out.append("")

    append_range = f"{cfg.worksheet}!A{cfg.header_row + 1}:Z"
    svc.spreadsheets().values().append(
        spreadsheetId=cfg.spreadsheet_id,
        range=append_range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_out]},
    ).execute()

    time.sleep(0.2)
    headers2, values2 = _get_headers_and_values_raw("subcategorias")
    idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        time.sleep(0.3)
        headers2, values2 = _get_headers_and_values_raw("subcategorias")
        idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        raise RuntimeError("Insert OK pero no pude re-encontrar la subcategoría por Timestamp")

    row_dict = _values_to_rows(headers2, [values2[idx]])[0]
    invalidate(get_current_spreadsheet_id(), "subcategorias")
    return {
        "id": str(row_dict.get("Id", "")).strip(),
        "categoria_id": str(row_dict.get("Id_Categoria", "")).strip(),
        "nombre": str(row_dict.get("Nombre_SubCategoria", "")).strip(),
    }


def patch_subcategoria_by_id(sub_id: str, nombre: str) -> Dict[str, Any]:
    """Actualiza el nombre de una subcategoría por Id."""
    cfg = SHEETS["subcategorias"]
    svc = get_sheets_service()
    headers, values = _get_headers_and_values_raw("subcategorias")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Sub-Categoria")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, sub_id)
    if idx is None:
        raise KeyError("Subcategoría no encontrada")

    if "Nombre_SubCategoria" not in headers:
        raise RuntimeError("La hoja Sub-Categoria no tiene columna Nombre_SubCategoria")

    row_number = cfg.header_row + 1 + idx
    col_letter = _col_to_a1(headers.index("Nombre_SubCategoria") + 1)
    a1 = f"{cfg.worksheet}!{col_letter}{row_number}"
    svc.spreadsheets().values().update(
        spreadsheetId=cfg.spreadsheet_id,
        range=a1,
        valueInputOption="USER_ENTERED",
        body={"values": [[nombre]]},
    ).execute()
    invalidate(get_current_spreadsheet_id(), "subcategorias")

    _, rows = read_table("subcategorias")
    for r in rows:
        if str(r.get("Id", "")).strip() == str(sub_id).strip():
            return {
                "id": str(r.get("Id", "")).strip(),
                "categoria_id": str(r.get("Id_Categoria", "")).strip(),
                "nombre": str(r.get("Nombre_SubCategoria", "")).strip(),
            }
    raise RuntimeError("Actualicé pero no pude leer la subcategoría")


def delete_subcategoria_by_id(sub_id: str) -> bool:
    """Elimina la fila de la subcategoría en Sheets."""
    cfg = SHEETS["subcategorias"]
    svc = get_sheets_service()
    headers, values = _get_headers_and_values_raw("subcategorias")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Sub-Categoria")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, sub_id)
    if idx is None:
        return False

    spreadsheet = svc.spreadsheets().get(spreadsheetId=cfg.spreadsheet_id).execute()
    sheet_id = None
    for s in spreadsheet.get("sheets", []):
        if s.get("properties", {}).get("title") == cfg.worksheet:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        raise RuntimeError("No se encontró la hoja Sub-Categoria")

    row_number = cfg.header_row + 1 + idx
    svc.spreadsheets().batchUpdate(
        spreadsheetId=cfg.spreadsheet_id,
        body={
            "requests": [{
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_number - 1,
                        "endIndex": row_number,
                    }
                }
            }]
        },
    ).execute()
    invalidate(get_current_spreadsheet_id(), "subcategorias")
    return True


def list_subcategorias(categoria_id: Optional[str] = None) -> List[Dict[str, Any]]:
    _, rows = read_table("subcategorias")
    # headers: Id_Categoria, Id, Nombre_SubCategoria
    out = []
    for r in rows:
        sid = str(r.get("Id", "")).strip()
        cid = str(r.get("Id_Categoria", "")).strip()
        if not sid:
            continue
        if categoria_id and cid != str(categoria_id).strip():
            continue
        out.append({
            "id": sid,
            "categoria_id": cid,
            "nombre": str(r.get("Nombre_SubCategoria", "")).strip(),
        })
    out.sort(key=lambda x: (x["categoria_id"], x["nombre"].lower()))
    return out


def list_reglas(
    comercio: Optional[str] = None,
    categoria_id: Optional[str] = None,
    subcategoria_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _, rows = read_table("reglas")
    # headers:
    # Id, Comercio, IdCategoria, Nombre_Categoria, IdSubCategoria, Nombre_SubCategoria, Timestamp
    out = []
    comercio_norm = comercio.strip().lower() if comercio else None

    for r in rows:
        rid = str(r.get("Id", "")).strip()
        if not rid:
            continue

        r_comercio = str(r.get("Comercio", "")).strip()
        r_cat_id = str(r.get("IdCategoria", "")).strip()
        r_sub_id = str(r.get("IdSubCategoria", "")).strip()

        if comercio_norm and comercio_norm not in r_comercio.lower():
            continue
        if categoria_id and r_cat_id != str(categoria_id).strip():
            continue
        if subcategoria_id and r_sub_id != str(subcategoria_id).strip():
            continue

        out.append({
            "id": rid,
            "comercio": r_comercio,
            "categoria_id": r_cat_id,
            "categoria_nombre": str(r.get("Nombre_Categoria", "")).strip(),
            "subcategoria_id": r_sub_id,
            "subcategoria_nombre": str(r.get("Nombre_SubCategoria", "")).strip(),
            "timestamp": str(r.get("Timestamp", "")).strip(),
        })

    # orden: comercio asc
    out.sort(key=lambda x: x["comercio"].lower())
    return out


# =========================
# Reglas: create, patch, delete (Sheets)
# =========================

def _get_merchant_name(merchant_id: str) -> str:
    """Resuelve merchant_id -> nombre. Los comercios están en store."""
    from app.storage.store import get_all
    merchants = get_all("merchants")
    for m in merchants:
        if str(m.get("id", "")).strip() == str(merchant_id).strip():
            return str(m.get("name", "")).strip()
    return ""


def create_regla(
    merchant_id: str,
    category_id: str,
    subcategory_id: Optional[str] = None,
    merchant_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crea una regla de comercio en Sheets.
    merchant_id -> Comercio (nombre del comercio desde store o merchant_name si se proporciona).
    Valida categoría y subcategoría.
    La hoja Reglas debe tener: Id, Comercio, IdCategoria, Nombre_Categoria, IdSubCategoria, Nombre_SubCategoria, Timestamp.
    """
    comercio = (merchant_name or "").strip() or _get_merchant_name(merchant_id)
    if not comercio:
        raise KeyError("Comercio no encontrado")

    if not get_categoria_by_id(category_id):
        raise KeyError("Categoría no encontrada")

    sub_id = (subcategory_id or "").strip()
    if sub_id:
        subs = list_subcategorias(categoria_id=category_id)
        if not any(str(s.get("id", "")).strip() == sub_id for s in subs):
            raise KeyError("Subcategoría no encontrada o no pertenece a la categoría")

    cat_nombre = _get_categoria_nombre(category_id)
    sub_nombre = _get_subcategoria_nombre(category_id, sub_id)

    cfg = SHEETS["reglas"]
    svc = get_sheets_service()
    headers, _ = _get_headers_and_values_raw("reglas")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Reglas")
    if "Timestamp" not in headers:
        raise RuntimeError("La hoja Reglas necesita columna 'Timestamp'.")

    ts = _now_timestamp_iso_local()
    row_out: List[Any] = []
    for h in headers:
        if h == cfg.id_column:
            row_out.append("")
        elif h == "Timestamp":
            row_out.append(ts)
        elif h == "Comercio":
            row_out.append(comercio)
        elif h == "IdCategoria":
            row_out.append(category_id)
        elif h == "Nombre_Categoria":
            row_out.append(cat_nombre)
        elif h == "IdSubCategoria":
            row_out.append(sub_id)
        elif h == "Nombre_SubCategoria":
            row_out.append(sub_nombre)
        else:
            row_out.append("")

    append_range = f"{cfg.worksheet}!A{cfg.header_row + 1}:Z"
    svc.spreadsheets().values().append(
        spreadsheetId=cfg.spreadsheet_id,
        range=append_range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_out]},
    ).execute()
    invalidate(get_current_spreadsheet_id(), "reglas")

    time.sleep(0.2)
    headers2, values2 = _get_headers_and_values_raw("reglas")
    idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        time.sleep(0.3)
        headers2, values2 = _get_headers_and_values_raw("reglas")
        idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        raise RuntimeError("Insert OK pero no pude re-encontrar la regla por Timestamp")

    row_dict = _values_to_rows(headers2, [values2[idx]])[0]
    result = _regla_row_to_response(row_dict)

    # Propagar a movimientos existentes con ese comercio
    _propagar_regla_a_movimientos(
        regla_comercio=comercio,
        cat_nombre=cat_nombre,
        sub_nombre=sub_nombre,
    )

    return result


def _regla_row_to_response(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row.get("Id", "")).strip(),
        "comercio": str(row.get("Comercio", "")).strip(),
        "categoria_id": str(row.get("IdCategoria", "")).strip(),
        "categoria_nombre": str(row.get("Nombre_Categoria", "")).strip(),
        "subcategoria_id": str(row.get("IdSubCategoria", "")).strip(),
        "subcategoria_nombre": str(row.get("Nombre_SubCategoria", "")).strip(),
        "timestamp": str(row.get("Timestamp", "")).strip(),
    }


def get_regla_by_id(regla_id: str) -> Optional[Dict[str, Any]]:
    _, rows = read_table("reglas")
    for r in rows:
        if str(r.get("Id", "")).strip() == str(regla_id).strip():
            return _regla_row_to_response(r)
    return None


def _comercio_matches_regla(mov_comercio: str, regla_comercio: str) -> bool:
    """
    Indica si el Comercio de un movimiento coincide con el patrón de la regla.
    Soporta patrones como "(?i)netflix" (case-insensitive).
    """
    search = re.sub(r"^\(\?i\)", "", str(regla_comercio or "").strip())
    if not search:
        return False
    return search.lower() in str(mov_comercio or "").strip().lower()


def _propagar_regla_a_movimientos(
    regla_comercio: str, cat_nombre: str, sub_nombre: str
) -> int:
    """
    Actualiza todos los movimientos cuyo Comercio coincide con la regla,
    asignando la nueva categoría y subcategoría. Retorna la cantidad actualizada.
    """
    _, rows = read_table("movimientos")
    count = 0
    for r in rows:
        mov_comercio = str(r.get("Comercio", "")).strip()
        if not _comercio_matches_regla(mov_comercio, regla_comercio):
            continue
        mov_id = str(r.get("Id", "")).strip()
        if not mov_id:
            continue
        patch_movimiento_by_id(
            mov_id,
            {"Nombre_Categoria": cat_nombre, "Nombre_SubCategoria": sub_nombre},
        )
        count += 1
    return count


def patch_regla_by_id(regla_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza regla por Id. No permite cambiar Id."""
    cfg = SHEETS["reglas"]
    svc = get_sheets_service()
    headers, values = _get_headers_and_values_raw("reglas")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Reglas")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, regla_id)
    if idx is None:
        raise KeyError("Regla no encontrada")

    row_number = cfg.header_row + 1 + idx
    updates = []

    if "comercio" in patch and "Comercio" in headers:
        updates.append(("Comercio", patch["comercio"]))
    if "categoria_id" in patch and "IdCategoria" in headers:
        cat_id = str(patch["categoria_id"]).strip()
        if not get_categoria_by_id(cat_id):
            raise KeyError("Categoría no encontrada")
        cat_nombre = _get_categoria_nombre(cat_id)
        updates.append(("IdCategoria", cat_id))
        if "Nombre_Categoria" in headers:
            updates.append(("Nombre_Categoria", cat_nombre))
    if "subcategoria_id" in patch and "IdSubCategoria" in headers:
        sub_id = (patch.get("subcategoria_id") or "").strip()
        cat_id = str(patch.get("categoria_id", "")).strip()
        if not cat_id:
            existing = get_regla_by_id(regla_id)
            cat_id = existing.get("categoria_id", "") if existing else ""
        if sub_id:
            subs = list_subcategorias(categoria_id=cat_id)
            if not any(str(s.get("id", "")).strip() == sub_id for s in subs):
                raise KeyError("Subcategoría no encontrada o no pertenece a la categoría")
        sub_nombre = _get_subcategoria_nombre(cat_id, sub_id)
        updates.append(("IdSubCategoria", sub_id))
        if "Nombre_SubCategoria" in headers:
            updates.append(("Nombre_SubCategoria", sub_nombre))

    if updates:
        data = []
        for col_name, val in updates:
            if col_name in headers:
                col_letter = _col_to_a1(headers.index(col_name) + 1)
                a1 = f"{cfg.worksheet}!{col_letter}{row_number}"
                data.append({"range": a1, "values": [[val]]})
        if data:
            svc.spreadsheets().values().batchUpdate(
                spreadsheetId=cfg.spreadsheet_id,
                body={"valueInputOption": "USER_ENTERED", "data": data},
            ).execute()
            invalidate(get_current_spreadsheet_id(), "reglas")

    updated = get_regla_by_id(regla_id)
    if not updated:
        raise RuntimeError("Actualicé pero no pude leer la regla")

    # Si se cambió categoría o subcategoría, propagar a todos los movimientos con ese comercio
    if "categoria_id" in patch or "subcategoria_id" in patch:
        _propagar_regla_a_movimientos(
            regla_comercio=updated["comercio"],
            cat_nombre=updated["categoria_nombre"],
            sub_nombre=updated["subcategoria_nombre"],
        )

    return updated


def delete_regla_by_id(regla_id: str) -> bool:
    """Elimina la fila de la regla en Sheets."""
    cfg = SHEETS["reglas"]
    svc = get_sheets_service()
    headers, values = _get_headers_and_values_raw("reglas")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Reglas")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, regla_id)
    if idx is None:
        return False

    spreadsheet = svc.spreadsheets().get(spreadsheetId=cfg.spreadsheet_id).execute()
    sheet_id = None
    for s in spreadsheet.get("sheets", []):
        if s.get("properties", {}).get("title") == cfg.worksheet:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        raise RuntimeError("No se encontró la hoja Reglas")

    row_number = cfg.header_row + 1 + idx
    svc.spreadsheets().batchUpdate(
        spreadsheetId=cfg.spreadsheet_id,
        body={
            "requests": [{
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_number - 1,
                        "endIndex": row_number,
                    }
                }
            }]
        },
    ).execute()
    invalidate(get_current_spreadsheet_id(), "reglas")
    return True


def list_presupuestos(
    mes_anio: Optional[str] = None,
    categoria_id: Optional[str] = None,
    subcategoria_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    from app.utils.parse_utils import normalize_mes_anio

    _, rows = read_table("presupuestos")
    # headers:
    # Id, mesAño, idCategoria, Nombre_Categoria, idSubcategoria, Nombre_SubCategoria, Monto

    mes_filter = normalize_mes_anio(mes_anio) if mes_anio else None
    if mes_filter is None and mes_anio:
        mes_filter = str(mes_anio).strip()

    out = []
    for r in rows:
        pid = str(r.get("Id", "")).strip()
        if not pid:
            continue

        r_mes = str(r.get("mesAño", "")).strip()
        r_mes_norm = normalize_mes_anio(r_mes) or r_mes
        r_cat = str(r.get("idCategoria", "")).strip()
        r_sub = str(r.get("idSubcategoria", "")).strip()

        if mes_filter and r_mes_norm != mes_filter:
            continue
        if categoria_id and r_cat != str(categoria_id).strip():
            continue
        if subcategoria_id and r_sub != str(subcategoria_id).strip():
            continue

        out.append({
            "id": pid,
            "mes_anio": r_mes,
            "categoria_id": r_cat,
            "categoria_nombre": str(r.get("Nombre_Categoria", "")).strip(),
            "subcategoria_id": r_sub,
            "subcategoria_nombre": str(r.get("Nombre_SubCategoria", "")).strip(),
            "monto": str(r.get("Monto", "")).strip(),
        })

    # orden: mes_anio desc (string) y luego categoria/subcategoria
    out.sort(key=lambda x: (x["mes_anio"], x["categoria_id"], x["subcategoria_id"]))
    return out


# =========================
# Presupuestos: create, patch, delete (Sheets)
# =========================

def _get_categoria_nombre(categoria_id: str) -> str:
    """Resuelve id -> nombre de categoría."""
    cats = list_categorias()
    for c in cats:
        if str(c.get("id", "")).strip() == str(categoria_id).strip():
            return c.get("nombre", "")
    return ""


def _get_subcategoria_nombre(categoria_id: str, subcategoria_id: str) -> str:
    """Resuelve id -> nombre de subcategoría. Vacío si subcategoria_id vacío (categoría general)."""
    if not subcategoria_id or not str(subcategoria_id).strip():
        return ""
    subs = list_subcategorias(categoria_id=categoria_id)
    for s in subs:
        if str(s.get("id", "")).strip() == str(subcategoria_id).strip():
            return s.get("nombre", "")
    return ""


def create_presupuesto(
    mes_anio: str,
    categoria_id: str,
    subcategoria_id: Optional[str],
    monto: float,
) -> Dict[str, Any]:
    """
    Crea un presupuesto en Sheets.
    - subcategoria_id vacío/None = presupuesto para toda la categoría (general).
    - Valida que categoría exista; si subcategoria_id viene, valida que exista y pertenezca a la categoría.
    La hoja Presupuesto debe tener: Id, mesAño, idCategoria, Nombre_Categoria, idSubcategoria, Nombre_SubCategoria, Monto, Timestamp.
    """
    from datetime import date
    from app.utils.parse_utils import normalize_mes_anio

    if not get_categoria_by_id(categoria_id):
        raise KeyError("Categoría no encontrada")
    sub_id = (subcategoria_id or "").strip()
    if sub_id:
        subs = list_subcategorias(categoria_id=categoria_id)
        found = any(str(s.get("id", "")).strip() == sub_id for s in subs)
        if not found:
            raise KeyError("Subcategoría no encontrada o no pertenece a la categoría")

    cat_nombre = _get_categoria_nombre(categoria_id)
    sub_nombre = _get_subcategoria_nombre(categoria_id, sub_id)
    mes_norm = normalize_mes_anio(mes_anio) if mes_anio else ""
    if not mes_norm:
        # Default: mes actual YYYY-MM
        today = date.today()
        mes_norm = f"{today.year}-{today.month:02d}"

    cfg = SHEETS["presupuestos"]
    svc = get_sheets_service()
    headers, _ = _get_headers_and_values_raw("presupuestos")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Presupuesto")
    if "Timestamp" not in headers:
        raise RuntimeError(
            "La hoja Presupuesto necesita columna 'Timestamp'. Agregá la columna Timestamp."
        )

    ts = _now_timestamp_iso_local()
    row_out: List[Any] = []
    for h in headers:
        if h == cfg.id_column:
            row_out.append("")
        elif h == "Timestamp":
            row_out.append(ts)
        elif h == "mesAño":
            row_out.append(mes_norm)
        elif h == "idCategoria":
            row_out.append(categoria_id)
        elif h == "Nombre_Categoria":
            row_out.append(cat_nombre)
        elif h == "idSubcategoria":
            row_out.append(sub_id)
        elif h == "Nombre_SubCategoria":
            row_out.append(sub_nombre)
        elif h == "Monto":
            row_out.append(monto)
        else:
            row_out.append("")

    append_range = f"{cfg.worksheet}!A{cfg.header_row + 1}:Z"
    svc.spreadsheets().values().append(
        spreadsheetId=cfg.spreadsheet_id,
        range=append_range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_out]},
    ).execute()
    invalidate(get_current_spreadsheet_id(), "presupuestos")

    time.sleep(0.2)
    headers2, values2 = _get_headers_and_values_raw("presupuestos")
    idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        time.sleep(0.3)
        headers2, values2 = _get_headers_and_values_raw("presupuestos")
        idx = _find_row_index_by_column_value(headers2, values2, "Timestamp", ts)
    if idx is None:
        raise RuntimeError("Insert OK pero no pude re-encontrar el presupuesto por Timestamp")

    row_dict = _values_to_rows(headers2, [values2[idx]])[0]
    return _presupuesto_row_to_response(row_dict)


def _presupuesto_row_to_response(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row.get("Id", "")).strip(),
        "mes_anio": str(row.get("mesAño", "")).strip(),
        "categoria_id": str(row.get("idCategoria", "")).strip(),
        "categoria_nombre": str(row.get("Nombre_Categoria", "")).strip(),
        "subcategoria_id": str(row.get("idSubcategoria", "")).strip(),
        "subcategoria_nombre": str(row.get("Nombre_SubCategoria", "")).strip(),
        "monto": str(row.get("Monto", "")).strip(),
    }


def get_presupuesto_by_id(presup_id: str) -> Optional[Dict[str, Any]]:
    _, rows = read_table("presupuestos")
    for r in rows:
        if str(r.get("Id", "")).strip() == str(presup_id).strip():
            return _presupuesto_row_to_response(r)
    return None


def patch_presupuesto_by_id(presup_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza presupuesto por Id. No permite cambiar Id."""
    cfg = SHEETS["presupuestos"]
    svc = get_sheets_service()
    headers, values = _get_headers_and_values_raw("presupuestos")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Presupuesto")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, presup_id)
    if idx is None:
        raise KeyError("Presupuesto no encontrado")

    row_number = cfg.header_row + 1 + idx
    updates = []
    if "mes_anio" in patch and "mesAño" in headers:
        from app.utils.parse_utils import normalize_mes_anio
        mes = normalize_mes_anio(str(patch["mes_anio"])) or str(patch["mes_anio"])
        col_letter = _col_to_a1(headers.index("mesAño") + 1)
        updates.append({"range": f"{cfg.worksheet}!{col_letter}{row_number}", "values": [[mes]]})
    if "monto" in patch and "Monto" in headers:
        val = patch["monto"]
        if isinstance(val, (int, float)):
            val = str(val)
        col_letter = _col_to_a1(headers.index("Monto") + 1)
        updates.append({"range": f"{cfg.worksheet}!{col_letter}{row_number}", "values": [[val]]})
    if "categoria_id" in patch and "idCategoria" in headers:
        cat_id = str(patch["categoria_id"]).strip()
        if get_categoria_by_id(cat_id):
            cat_nombre = _get_categoria_nombre(cat_id)
            for col_name, val in [("idCategoria", cat_id), ("Nombre_Categoria", cat_nombre)]:
                if col_name in headers:
                    col_letter = _col_to_a1(headers.index(col_name) + 1)
                    updates.append({"range": f"{cfg.worksheet}!{col_letter}{row_number}", "values": [[val]]})
    if "subcategoria_id" in patch and "idSubcategoria" in headers:
        sub_id = (patch["subcategoria_id"] or "").strip()
        cat_id = str(patch.get("categoria_id", "")).strip()
        if not cat_id:
            existing = get_presupuesto_by_id(presup_id)
            cat_id = existing.get("categoria_id", "") if existing else ""
        sub_nombre = _get_subcategoria_nombre(cat_id, sub_id)
        for col_name, val in [("idSubcategoria", sub_id), ("Nombre_SubCategoria", sub_nombre)]:
            if col_name in headers:
                col_letter = _col_to_a1(headers.index(col_name) + 1)
                updates.append({"range": f"{cfg.worksheet}!{col_letter}{row_number}", "values": [[val]]})

    if updates:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=cfg.spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": updates},
        ).execute()
        invalidate(get_current_spreadsheet_id(), "presupuestos")

    updated = get_presupuesto_by_id(presup_id)
    if not updated:
        raise RuntimeError("Actualicé pero no pude leer el presupuesto")
    return updated


def delete_presupuesto_by_id(presup_id: str) -> bool:
    """Elimina la fila del presupuesto en Sheets."""
    cfg = SHEETS["presupuestos"]
    svc = get_sheets_service()
    headers, values = _get_headers_and_values_raw("presupuestos")
    if not headers:
        raise RuntimeError("No se pudieron leer headers de Presupuesto")

    idx = _find_row_index_by_column_value(headers, values, cfg.id_column, presup_id)
    if idx is None:
        return False

    spreadsheet = svc.spreadsheets().get(spreadsheetId=cfg.spreadsheet_id).execute()
    sheet_id = None
    for s in spreadsheet.get("sheets", []):
        if s.get("properties", {}).get("title") == cfg.worksheet:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        raise RuntimeError("No se encontró la hoja Presupuesto")

    row_number = cfg.header_row + 1 + idx
    svc.spreadsheets().batchUpdate(
        spreadsheetId=cfg.spreadsheet_id,
        body={
            "requests": [{
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_number - 1,
                        "endIndex": row_number,
                    }
                }
            }]
        },
    ).execute()
    invalidate(get_current_spreadsheet_id(), "presupuestos")
    return True
