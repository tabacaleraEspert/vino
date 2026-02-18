"""
Servicio de dominio para la vista Home (tarjeta Gastado/Presupuesto/Usado%).
Lee de Sheets: movimientos y presupuestos.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.sheets.service import read_table
from app.utils.parse_utils import (
    parse_date_ddmmyyyy,
    parse_money,
    parse_period,
    normalize_mes_anio,
)


def get_home_summary(
    period: str,
    user_id: Optional[str] = None,
    moneda: str = "ARS",
) -> Dict[str, Any]:
    """
    Calcula gasto_mes y presupuesto_mes para la tarjeta de inicio.
    - gasto_mes: suma de Monto donde Tipo de Movimiento == "gasto" (case insensitive)
      en el rango de fechas del period, filtrado por user_id y moneda.
    - presupuesto_mes: suma de Monto en Presupuesto donde mesAño coincide con period.
    """
    date_from, date_to = parse_period(period)
    period_norm = normalize_mes_anio(period)
    if not period_norm:
        period_norm = period

    # 1) Movimientos -> gasto_mes
    _, mov_rows = read_table("movimientos")
    print(f"[home_summary] period={period} user_id={user_id} moneda={moneda} mov_rows={len(mov_rows)}")
    gasto_mes = 0.0
    moneda_upper = (moneda or "ARS").strip().upper()

    for i, r in enumerate(mov_rows):
        tipo = str(r.get("Tipo de Movimiento", "")).strip().lower()
        if tipo != "gasto":
            print(f"[home_summary] row {i} skip: tipo={tipo!r} != 'gasto'")
            continue
        # Cada usuario tiene su propio spreadsheet; no filtrar por Id_usuario
        r_moneda = str(r.get("Moneda", "")).strip().upper()
        if r_moneda and r_moneda != moneda_upper:
            print(f"[home_summary] row {i} skip: Moneda={r_moneda!r} != {moneda_upper!r}")
            continue
        r_fecha = parse_date_ddmmyyyy(r.get("Fecha"))
        if not r_fecha or r_fecha < date_from or r_fecha > date_to:
            print(f"[home_summary] row {i} skip: Fecha={r.get('Fecha')!r} -> parsed={r_fecha} range=[{date_from}, {date_to}]")
            continue
        gasto_mes += parse_money(r.get("Monto"))

    # 2) Presupuesto -> presupuesto_mes
    _, presup_rows = read_table("presupuestos")
    presupuesto_mes = 0.0

    for r in presup_rows:
        r_mes = str(r.get("mesAño", "")).strip()
        r_mes_norm = normalize_mes_anio(r_mes)
        if not r_mes_norm:
            r_mes_norm = r_mes
        if r_mes_norm != period_norm:
            continue
        presupuesto_mes += parse_money(r.get("Monto"))

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
    moneda_upper = (currency or "ARS").strip().upper()

    _, mov_rows = read_table("movimientos")
    gastos: list[Dict[str, Any]] = []
    total_gastos = 0.0

    for r in mov_rows:
        tipo = str(r.get("Tipo de Movimiento", "")).strip().lower()
        if tipo != "gasto":
            continue
        # Cada usuario tiene su propio spreadsheet; no filtrar por Id_usuario
        r_moneda = str(r.get("Moneda", "")).strip().upper()
        if r_moneda and r_moneda != moneda_upper:
            continue
        r_fecha = parse_date_ddmmyyyy(r.get("Fecha"))
        if not r_fecha or r_fecha < date_from or r_fecha > date_to:
            continue
        monto = parse_money(r.get("Monto"))
        total_gastos += monto
        cat = str(r.get("Nombre_Categoria", "")).strip() or "Sin categoría"
        gastos.append({
            "row": r,
            "categoria": cat,
            "subcategoria": str(r.get("Nombre_SubCategoria", "")).strip(),
            "monto": monto,
            "fecha": r_fecha,
            "timestamp": str(r.get("Timestamp", "")).strip(),
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
        from app.sheets.catalog_service import list_categorias
        cats = {c["nombre"] for c in list_categorias()}
        for c in cats:
            if c not in by_cat:
                gastos_por_categoria.append({"categoria": c, "total": 0.0, "pct": 0.0})
        gastos_por_categoria.sort(key=lambda x: -x["total"])

    # Transacciones recientes (orden por fecha desc, luego timestamp)
    gastos_sorted = sorted(gastos, key=lambda g: (g["fecha"], g["timestamp"]), reverse=True)
    transacciones_recientes = []
    for g in gastos_sorted[:recent_limit]:
        r = g["row"]
        comercio = str(r.get("Comercio", "")).strip()
        desc = str(r.get("Descripcion", "")).strip()
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
