"""
Servicio de dominio para la vista Home (tarjeta Gastado/Presupuesto/Usado%).
Lee movimientos desde SQL o Sheets según MOVIMIENTOS_USE_SQL; presupuestos desde SQL.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import settings
from app.sheets.service import read_table
from app.utils.parse_utils import (
    parse_date_ddmmyyyy,
    parse_date_flex,
    parse_money,
    parse_period,
    normalize_mes_anio,
)

USE_SQL = getattr(settings, "MOVIMIENTOS_USE_SQL", True)


def _get_movimientos_for_period(
    date_from,
    date_to,
    user_id: Optional[str],
    moneda: str,
):
    """Obtiene movimientos gasto en el período. Desde SQL o Sheets."""
    moneda_upper = (moneda or "ARS").strip().upper()
    if USE_SQL and user_id:
        try:
            from app.db.movimientos import list_movimientos as sql_list

            id_usuario = int(user_id)
            items, _ = sql_list(
                id_usuario=id_usuario,
                from_date=date_from,
                to_date=date_to,
                tipo="Gasto",
                moneda=moneda_upper if moneda_upper else None,
                limit=10000,
                offset=0,
            )
            out_items = []
            for it in items:
                f = parse_date_flex(it.get("fecha") or it.get("Fecha"))
                out_items.append({
                    "row": it,
                    "monto": float(it.get("monto") or it.get("Monto") or 0),
                    "categoria": it.get("categoria") or it.get("Nombre_Categoria") or "Sin categoría",
                    "subcategoria": it.get("subcategoria") or it.get("Nombre_SubCategoria") or "",
                    "fecha": f or date_from,
                    "timestamp": it.get("timestamp") or it.get("Timestamp") or "",
                    "comercio": it.get("comercio") or it.get("Comercio") or "",
                    "descripcion": it.get("descripcion") or it.get("Descripcion") or "",
                })
            return out_items
        except (ValueError, TypeError, Exception):
            pass

    _, mov_rows = read_table("movimientos")
    out = []
    for r in mov_rows:
        tipo = str(r.get("Tipo de Movimiento", "")).strip().lower()
        if tipo != "gasto":
            continue
        r_moneda = str(r.get("Moneda", "")).strip().upper()
        if r_moneda and r_moneda != moneda_upper:
            continue
        r_fecha = parse_date_ddmmyyyy(r.get("Fecha"))
        if not r_fecha or r_fecha < date_from or r_fecha > date_to:
            continue
        out.append({
            "row": r,
            "monto": parse_money(r.get("Monto")),
            "categoria": str(r.get("Nombre_Categoria", "")).strip() or "Sin categoría",
            "subcategoria": str(r.get("Nombre_SubCategoria", "")).strip(),
            "fecha": r_fecha,
            "timestamp": str(r.get("Timestamp", "")).strip(),
            "comercio": str(r.get("Comercio", "")).strip(),
            "descripcion": str(r.get("Descripcion", "")).strip(),
        })
    return out


def get_home_summary(
    period: str,
    user_id: Optional[str] = None,
    moneda: str = "ARS",
) -> Dict[str, Any]:
    """
    Calcula gasto_mes y presupuesto_mes para la tarjeta de inicio.
    - gasto_mes: suma de Monto donde Tipo de Movimiento == "gasto" (case insensitive)
      en el rango de fechas del period, filtrado por user_id y moneda.
    - presupuesto_mes: suma de Monto desde SQL Presupuestos (multi-tenant).
    """
    from app.utils.parse_utils import parse_periodo_mes
    from app.db.presupuestos import list_presupuestos_sql

    date_from, date_to = parse_period(period)
    period_norm = normalize_mes_anio(period)
    if not period_norm:
        period_norm = period

    # 1) Movimientos -> gasto_mes (SQL o Sheets)
    mov_rows = _get_movimientos_for_period(date_from, date_to, user_id, moneda)
    gasto_mes = sum(g["monto"] for g in mov_rows)

    # 2) Presupuesto -> presupuesto_mes (desde SQL)
    presupuesto_mes = 0.0
    if user_id:
        try:
            id_usuario = int(user_id)
            periodo_mes = parse_periodo_mes(period)
            presup_rows = list_presupuestos_sql(id_usuario, periodo_mes=periodo_mes)
            for r in presup_rows:
                presupuesto_mes += float(r.get("Monto", r.get("monto", 0)) or 0)
        except (ValueError, TypeError, Exception):
            pass

    return {
        "period": period,
        "user_id": user_id,
        "moneda": moneda or "ARS",
        "gasto_mes": round(gasto_mes, 2),
        "presupuesto_mes": round(presupuesto_mes, 2),
    }


def get_home_breakdown(
    period: str,
    user_id: Optional[str] = None,
    currency: str = "ARS",
    top_categories: int = 6,
    recent_limit: int = 5,
    include_zeros: bool = False,
) -> Dict[str, Any]:
    """
    Gastos por categoría (top N), transacciones recientes, mayor_gasto, transacciones_count.
    """
    date_from, date_to = parse_period(period)

    mov_rows = _get_movimientos_for_period(date_from, date_to, user_id, currency)
    gastos: list[Dict[str, Any]] = []
    total_gastos = 0.0

    for g in mov_rows:
        monto = g["monto"]
        total_gastos += monto
        gastos.append({
            "row": g["row"],
            "categoria": g["categoria"],
            "subcategoria": g["subcategoria"],
            "monto": monto,
            "fecha": g["fecha"],
            "timestamp": g["timestamp"],
        })

    # Gastos por categoría (agrupado)
    by_cat: Dict[str, float] = {}
    for g in gastos:
        c = g["categoria"]
        by_cat[c] = by_cat.get(c, 0) + g["monto"]

    sorted_cats = sorted(by_cat.items(), key=lambda x: -x[1])
    gastos_por_categoria = []
    for cat, total in sorted_cats[:top_categories]:
        pct = round(total / total_gastos, 2) if total_gastos > 0 else 0.0
        gastos_por_categoria.append({"categoria": cat, "total": round(total, 2), "pct": pct})

    if include_zeros:
        cats = set()
        if USE_SQL and user_id:
            try:
                from app.db.catalog import list_categorias_sql
                cats = {c["nombre"] for c in list_categorias_sql(int(user_id))}
            except (ValueError, TypeError, Exception):
                pass
        if not cats:
            try:
                from app.sheets.catalog_service import list_categorias
                cats = {c["nombre"] for c in list_categorias()}
            except Exception:
                pass
        for c in cats:
            if c not in by_cat:
                gastos_por_categoria.append({"categoria": c, "total": 0.0, "pct": 0.0})
        gastos_por_categoria.sort(key=lambda x: -x["total"])

    # Transacciones recientes (orden por fecha desc, luego timestamp)
    gastos_sorted = sorted(gastos, key=lambda g: (g["fecha"], g["timestamp"]), reverse=True)
    transacciones_recientes = []
    for g in gastos_sorted[:recent_limit]:
        r = g["row"]
        comercio = str(r.get("Comercio") or r.get("comercio") or "").strip()
        desc = str(r.get("Descripcion") or r.get("descripcion") or "").strip()
        titulo = comercio or desc or "Sin descripción"
        transacciones_recientes.append({
            "id": str(r.get("Id", "")).strip(),
            "fecha": g["fecha"].strftime("%Y-%m-%d"),
            "timestamp": g["timestamp"] or "",
            "titulo": titulo,
            "descripcion": desc or titulo,
            "comercio": comercio,
            "categoria": g["categoria"],
            "subcategoria": g["subcategoria"],
            "monto": round(g["monto"], 2),
        })

    mayor_gasto = max((g["monto"] for g in gastos), default=0.0)

    return {
        "period": period,
        "user_id": user_id,
        "currency": currency or "ARS",
        "gastos_por_categoria": gastos_por_categoria,
        "transacciones_recientes": transacciones_recientes,
        "mayor_gasto": round(mayor_gasto, 2),
        "transacciones_count": len(gastos),
    }
