from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id

router = APIRouter()


@router.get("/summary")
async def get_home_summary(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2025-10"),
    moneda: str = Query(default="ARS"),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Resumen para la tarjeta de Inicio: gasto del mes y presupuesto."""
    from app.utils.parse_utils import parse_period, parse_periodo_mes, normalize_mes_anio
    from app.repositories.movimiento_repo import list_movimientos
    from app.repositories.presupuesto_repo import list_presupuestos

    try:
        date_from, date_to = parse_period(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Gasto del mes
    items, _ = await list_movimientos(
        db, id_usuario, from_date=date_from, to_date=date_to,
        tipo="Gasto", moneda=moneda.strip().upper(), limit=5000, offset=0,
    )
    gasto_mes = sum(float(it.get("monto", 0)) for it in items)

    # Presupuesto del mes
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
        "moneda": moneda or "ARS",
        "gasto_mes": round(gasto_mes, 2),
        "presupuesto_mes": round(presupuesto_mes, 2),
    }


@router.get("/breakdown")
async def get_home_breakdown(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2026-02"),
    currency: str = Query(default="ARS"),
    top_categories: int = Query(default=6, ge=1, le=20),
    recent_limit: int = Query(default=5, ge=1, le=50),
    include_zeros: bool = Query(default=False),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Gastos por categoría (top N), transacciones recientes."""
    from app.utils.parse_utils import parse_period
    from app.repositories.movimiento_repo import list_movimientos
    from app.repositories.categoria_repo import list_categorias

    try:
        date_from, date_to = parse_period(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    items, _ = await list_movimientos(
        db, id_usuario, from_date=date_from, to_date=date_to,
        tipo="Gasto", moneda=currency.strip().upper(), limit=5000, offset=0,
    )

    total_gastos = 0.0
    by_cat = {}
    for it in items:
        monto = float(it.get("monto", 0))
        total_gastos += monto
        cat = it.get("categoria") or it.get("Nombre_Categoria") or "Sin categoría"
        by_cat[cat] = by_cat.get(cat, 0) + monto

    sorted_cats = sorted(by_cat.items(), key=lambda x: -x[1])
    gastos_por_categoria = []
    for cat, total in sorted_cats[:top_categories]:
        pct = round(total / total_gastos, 2) if total_gastos > 0 else 0.0
        gastos_por_categoria.append({"categoria": cat, "total": round(total, 2), "pct": pct})

    if include_zeros:
        cats_db = await list_categorias(db, id_usuario)
        for c in cats_db:
            if c["nombre"] not in by_cat:
                gastos_por_categoria.append({"categoria": c["nombre"], "total": 0.0, "pct": 0.0})
        gastos_por_categoria.sort(key=lambda x: -x["total"])

    # Recent transactions
    sorted_items = sorted(items, key=lambda g: (g.get("fecha", ""), g.get("timestamp", "")), reverse=True)
    transacciones_recientes = []
    for it in sorted_items[:recent_limit]:
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

    mayor_gasto = max((float(it.get("monto", 0)) for it in items), default=0.0)

    return {
        "period": period,
        "user_id": str(id_usuario),
        "currency": currency or "ARS",
        "gastos_por_categoria": gastos_por_categoria,
        "transacciones_recientes": transacciones_recientes,
        "mayor_gasto": round(mayor_gasto, 2),
        "transacciones_count": len(items),
    }
