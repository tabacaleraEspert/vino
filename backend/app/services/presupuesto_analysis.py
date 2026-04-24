"""Service for budget vs actual spending analysis and smart suggestions."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.movimiento_repo import list_movimientos
from app.repositories.presupuesto_repo import list_presupuestos
from app.utils.parse_utils import parse_period


async def budget_vs_actual(
    db: AsyncSession,
    id_usuario: int,
    period: str,
    moneda: str = "ARS",
) -> dict[str, Any]:
    """
    Compare budgets vs actual spending for a given period.

    Returns per-category breakdown with: budgeted, spent, remaining, pct_used,
    plus overall totals.
    """
    date_from, date_to = parse_period(period)
    periodo_mes = date(date_from.year, date_from.month, 1)

    # Fetch budgets and movements in parallel-ish (both async)
    presup_rows = await list_presupuestos(db, id_usuario, periodo_mes=periodo_mes)
    items, _ = await list_movimientos(
        db, id_usuario, from_date=date_from, to_date=date_to,
        tipo="Gasto", moneda=moneda, limit=5000, offset=0,
    )

    # Aggregate spending by category ID
    spending_by_cat: dict[str, float] = {}
    spending_by_cat_name: dict[str, float] = {}
    for it in items:
        cat_id = str(it.get("Id_Categoria") or it.get("idCategoria") or "")
        cat_name = it.get("categoria") or it.get("Nombre_Categoria") or "Sin categoría"
        monto = float(it.get("monto", 0))
        spending_by_cat[cat_id] = spending_by_cat.get(cat_id, 0) + monto
        spending_by_cat_name[cat_name] = spending_by_cat_name.get(cat_name, 0) + monto

    # Build per-category comparison
    categorias = []
    total_budgeted = 0.0
    total_spent = 0.0
    cats_with_budget = set()

    for p in presup_rows:
        cat_id = str(p.get("categoria_id", ""))
        cat_name = p.get("categoria_nombre", "") or "Sin categoría"
        budgeted = float(p.get("monto", 0))
        spent = spending_by_cat.get(cat_id, 0)
        remaining = budgeted - spent
        pct_used = round(spent / budgeted * 100, 1) if budgeted > 0 else 0

        categorias.append({
            "categoria_id": cat_id,
            "categoria": cat_name,
            "presupuesto": round(budgeted, 2),
            "gastado": round(spent, 2),
            "restante": round(remaining, 2),
            "pct_usado": pct_used,
        })

        total_budgeted += budgeted
        total_spent += spent
        cats_with_budget.add(cat_id)

    # Add categories with spending but no budget
    for cat_name, spent in spending_by_cat_name.items():
        # Find cat_id for this name
        cat_id = None
        for it in items:
            if (it.get("categoria") or it.get("Nombre_Categoria")) == cat_name:
                cat_id = str(it.get("Id_Categoria") or it.get("idCategoria") or "")
                break
        if cat_id and cat_id not in cats_with_budget:
            categorias.append({
                "categoria_id": cat_id,
                "categoria": cat_name,
                "presupuesto": 0,
                "gastado": round(spent, 2),
                "restante": round(-spent, 2),
                "pct_usado": 0,
            })
            total_spent += spent

    # Sort by pct_used descending (most over-budget first)
    categorias.sort(key=lambda x: x["pct_usado"], reverse=True)

    # Days info for the period
    today = date.today()
    days_in_month = (date_to - date_from).days + 1
    if today < date_from:
        days_elapsed = 0
    elif today > date_to:
        days_elapsed = days_in_month
    else:
        days_elapsed = (today - date_from).days + 1
    days_remaining = max(0, days_in_month - days_elapsed)

    return {
        "period": period,
        "moneda": moneda,
        "dias_transcurridos": days_elapsed,
        "dias_restantes": days_remaining,
        "total_presupuesto": round(total_budgeted, 2),
        "total_gastado": round(total_spent, 2),
        "total_restante": round(total_budgeted - total_spent, 2),
        "pct_usado_global": round(total_spent / total_budgeted * 100, 1) if total_budgeted > 0 else 0,
        "categorias": categorias,
    }


async def generate_suggestions(
    db: AsyncSession,
    id_usuario: int,
    period: str,
    moneda: str = "ARS",
) -> list[dict[str, Any]]:
    """
    Generate smart financial suggestions based on budget vs actual data.

    Rules:
    - Over budget (>100%): alert
    - Near limit (>75%): warning
    - On track with days remaining: positive reinforcement
    - No budget set but high spending: suggest setting one
    - Compare pace: projected vs budgeted
    """
    analysis = await budget_vs_actual(db, id_usuario, period, moneda)
    suggestions: list[dict[str, Any]] = []

    days_elapsed = analysis["dias_transcurridos"]
    days_remaining = analysis["dias_restantes"]
    days_in_month = days_elapsed + days_remaining
    pct_month_elapsed = round(days_elapsed / days_in_month * 100, 1) if days_in_month > 0 else 100

    for cat in analysis["categorias"]:
        presupuesto = cat["presupuesto"]
        gastado = cat["gastado"]
        pct_usado = cat["pct_usado"]
        categoria = cat["categoria"]

        if presupuesto <= 0:
            # No budget but spending exists
            if gastado > 0:
                suggestions.append({
                    "tipo": "info",
                    "categoria": categoria,
                    "mensaje": f"Gastaste ${gastado:,.0f} en {categoria} sin presupuesto definido. Considerá poner un límite.",
                })
            continue

        restante = cat["restante"]

        if pct_usado > 100:
            # Over budget
            exceso = gastado - presupuesto
            suggestions.append({
                "tipo": "alerta",
                "categoria": categoria,
                "mensaje": f"Te pasaste del presupuesto de {categoria} por ${exceso:,.0f}. Gastaste ${gastado:,.0f} de ${presupuesto:,.0f}.",
                "pct_usado": pct_usado,
            })
        elif pct_usado > 75:
            # Near limit
            if days_remaining > 5:
                diario_restante = restante / days_remaining if days_remaining > 0 else 0
                suggestions.append({
                    "tipo": "advertencia",
                    "categoria": categoria,
                    "mensaje": f"Llevás el {pct_usado}% de {categoria} y faltan {days_remaining} días. Te quedan ${restante:,.0f} (${diario_restante:,.0f}/día).",
                    "pct_usado": pct_usado,
                })
            else:
                suggestions.append({
                    "tipo": "advertencia",
                    "categoria": categoria,
                    "mensaje": f"Llevás el {pct_usado}% de {categoria} con {days_remaining} días restantes. Cuidado con los gastos.",
                    "pct_usado": pct_usado,
                })
        elif pct_usado > 50 and pct_usado > pct_month_elapsed + 10:
            # Spending pace ahead of calendar pace
            projected = gastado / days_elapsed * days_in_month if days_elapsed > 0 else 0
            if projected > presupuesto:
                suggestions.append({
                    "tipo": "advertencia",
                    "categoria": categoria,
                    "mensaje": f"A este ritmo vas a gastar ~${projected:,.0f} en {categoria} (presupuesto: ${presupuesto:,.0f}). Ajustá el gasto.",
                    "pct_usado": pct_usado,
                })
        elif pct_usado <= 50 and days_elapsed > days_in_month / 2:
            # Under budget and past mid-month — positive
            suggestions.append({
                "tipo": "positivo",
                "categoria": categoria,
                "mensaje": f"Bien en {categoria}: gastaste solo el {pct_usado}% del presupuesto con más de la mitad del mes pasado.",
                "pct_usado": pct_usado,
            })

    # Global suggestion
    total_pct = analysis["pct_usado_global"]
    if total_pct > 100:
        suggestions.insert(0, {
            "tipo": "alerta",
            "categoria": "TOTAL",
            "mensaje": f"Superaste el presupuesto total del mes. Gastaste ${analysis['total_gastado']:,.0f} de ${analysis['total_presupuesto']:,.0f}.",
            "pct_usado": total_pct,
        })
    elif total_pct > 80 and days_remaining > 3:
        suggestions.insert(0, {
            "tipo": "advertencia",
            "categoria": "TOTAL",
            "mensaje": f"Llevás el {total_pct}% del presupuesto total y faltan {days_remaining} días. Quedan ${analysis['total_restante']:,.0f}.",
            "pct_usado": total_pct,
        })

    # Sort: alertas first, then advertencias, then info, then positivo
    priority = {"alerta": 0, "advertencia": 1, "info": 2, "positivo": 3}
    suggestions.sort(key=lambda x: priority.get(x["tipo"], 9))

    return suggestions
