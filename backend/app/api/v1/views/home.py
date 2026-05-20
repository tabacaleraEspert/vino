from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.utils.parse_utils import parse_period, parse_periodo_mes
from app.repositories.movimiento_agg import (
    sum_gastos_mes,
    sum_ingresos_mes,
    gastos_por_categoria,
    ingresos_por_categoria,
    mayor_gasto_mes,
    count_gastos_mes,
)
from app.repositories.presupuesto_repo import list_presupuestos
from app.repositories.movimiento_repo import list_movimientos
from app.repositories.categoria_repo import list_categorias

router = APIRouter()


@router.get("/summary")
async def get_home_summary(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2025-10"),
    moneda: str = Query(default="ARS"),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Resumen: gasto del mes y presupuesto. Uses SQL SUM, not Python loop."""
    try:
        date_from, date_to = parse_period(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    currency = moneda.strip().upper()

    # SQL-level aggregation — single query each
    gasto_mes, ingreso_mes = await sum_gastos_mes(db, id_usuario, date_from, date_to, currency), \
        await sum_ingresos_mes(db, id_usuario, date_from, date_to, currency)

    presupuesto_mes = 0.0
    try:
        periodo_mes = parse_periodo_mes(period)
        presup_rows = await list_presupuestos(db, id_usuario, periodo_mes=periodo_mes)
        presupuesto_mes = sum(float(r.get("monto", 0)) for r in presup_rows)
    except (ValueError, TypeError):
        pass

    return {
        "period": period,
        "user_id": str(id_usuario),
        "moneda": currency,
        "gasto_mes": round(gasto_mes, 2),
        "ingreso_mes": round(ingreso_mes, 2),
        "balance_mes": round(ingreso_mes - gasto_mes, 2),
        "presupuesto_mes": round(presupuesto_mes, 2),
    }


@router.get("/breakdown")
async def get_home_breakdown(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2026-02"),
    currency: str = Query(default="ARS"),
    tipo: str = Query(default="Gasto", description="Gasto o Ingreso"),
    top_categories: int = Query(default=6, ge=1, le=20),
    recent_limit: int = Query(default=5, ge=1, le=50),
    include_zeros: bool = Query(default=False),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Movimientos por categoría + transacciones recientes. SQL GROUP BY, not Python loop."""
    try:
        date_from, date_to = parse_period(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cur = currency.strip().upper()

    tipo_norm = "Ingreso" if tipo.strip().lower() == "ingreso" else "Gasto"

    # SQL-level aggregations — much faster than loading all rows
    if tipo_norm == "Ingreso":
        cat_rows = await ingresos_por_categoria(db, id_usuario, date_from, date_to, cur, top_categories)
    else:
        cat_rows = await gastos_por_categoria(db, id_usuario, date_from, date_to, cur, top_categories)
    total_gastos = sum(r["total"] for r in cat_rows)
    mayor = await mayor_gasto_mes(db, id_usuario, date_from, date_to, cur)
    tx_count = await count_gastos_mes(db, id_usuario, date_from, date_to, cur)

    # Build category breakdown with percentages
    # Get all categories for icon/color mapping
    all_cats = await list_categorias(db, id_usuario)
    cat_map = {c["id"]: c for c in all_cats}

    gastos_por_cat = []
    for r in cat_rows:
        cat_info = cat_map.get(r["categoria_id"], {})
        pct = round(r["total"] / total_gastos, 2) if total_gastos > 0 else 0.0
        gastos_por_cat.append({
            "categoria": r["categoria"],
            "total": round(r["total"], 2),
            "pct": pct,
            "icon": cat_info.get("icon", "📁"),
            "color": cat_info.get("color", "#6b7280"),
        })

    if include_zeros:
        existing = {r["categoria"] for r in cat_rows}
        for c in all_cats:
            if c["nombre"] not in existing:
                gastos_por_cat.append({
                    "categoria": c["nombre"],
                    "total": 0.0,
                    "pct": 0.0,
                    "icon": c.get("icon", "📁"),
                    "color": c.get("color", "#6b7280"),
                })

    # Recent transactions — only fetch the few we need
    items, _ = await list_movimientos(
        db, id_usuario, from_date=date_from, to_date=date_to,
        tipo=tipo_norm, moneda=cur, limit=recent_limit, offset=0,
    )

    transacciones_recientes = []
    for it in sorted(items, key=lambda g: (g.get("fecha", ""), g.get("timestamp", "")), reverse=True)[:recent_limit]:
        comercio = str(it.get("comercio") or it.get("Comercio") or "").strip()
        desc = str(it.get("descripcion") or it.get("Descripcion") or "").strip()
        titulo = comercio or desc or "Sin descripción"
        transacciones_recientes.append({
            "id": str(it.get("id", "")),
            "fecha": it.get("fecha", ""),
            "timestamp": it.get("timestamp", ""),
            "titulo": titulo,
            "descripcion": desc or titulo,
            "comercio": comercio,
            "categoria": it.get("categoria", ""),
            "subcategoria": it.get("subcategoria", ""),
            "monto": round(float(it.get("monto", 0)), 2),
        })

    return {
        "period": period,
        "user_id": str(id_usuario),
        "currency": cur,
        "gastos_por_categoria": gastos_por_cat,
        "transacciones_recientes": transacciones_recientes,
        "mayor_gasto": round(mayor, 2),
        "transacciones_count": tx_count,
    }
