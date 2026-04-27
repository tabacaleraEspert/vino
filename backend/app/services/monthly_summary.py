"""Monthly summary — end-of-month report with grades, insights and suggestions."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.movimiento_agg import (
    sum_gastos_mes,
    gastos_por_categoria,
    count_gastos_mes,
    mayor_gasto_mes,
    avg_ticket_por_categoria,
    gastos_categoria_por_periodo,
)
from app.repositories.presupuesto_repo import list_presupuestos
from app.utils.parse_utils import parse_period

logger = logging.getLogger(__name__)


def _fmt(n: float) -> str:
    return f"${n:,.0f}".replace(",", ".")


async def generate_monthly_summary(
    db: AsyncSession,
    id_usuario: int,
    period: str,
    moneda: str = "ARS",
) -> dict[str, Any]:
    """
    Generate a comprehensive monthly summary.
    Returns structured data + WhatsApp-formatted message.
    """
    date_from, date_to = parse_period(period)
    periodo_mes = date(date_from.year, date_from.month, 1)

    # Core metrics
    total_spent = await sum_gastos_mes(db, id_usuario, date_from, date_to, moneda)
    tx_count = await count_gastos_mes(db, id_usuario, date_from, date_to, moneda)
    biggest = await mayor_gasto_mes(db, id_usuario, date_from, date_to, moneda)
    cat_breakdown = await gastos_por_categoria(db, id_usuario, date_from, date_to, moneda, top=10)

    # Budget
    presup_rows = await list_presupuestos(db, id_usuario, periodo_mes=periodo_mes)
    total_budget = sum(float(r.get("monto", 0)) for r in presup_rows)

    # Per-category budget comparison
    budget_by_cat: dict[str, float] = {}
    for p in presup_rows:
        cat_name = p.get("categoria_nombre", "")
        if cat_name:
            budget_by_cat[cat_name] = budget_by_cat.get(cat_name, 0) + float(p.get("monto", 0))

    # Previous month comparison
    prev_month = periodo_mes - timedelta(days=1)
    prev_period = f"{prev_month.year}-{prev_month.month:02d}"
    try:
        prev_from, prev_to = parse_period(prev_period)
        prev_total = await sum_gastos_mes(db, id_usuario, prev_from, prev_to, moneda)
    except Exception:
        prev_total = 0

    # Category analysis
    categories_analysis = []
    over_budget = []
    under_budget = []

    for cat in cat_breakdown:
        cat_name = cat["categoria"]
        spent = cat["total"]
        budget = budget_by_cat.get(cat_name, 0)
        pct_of_total = (spent / total_spent * 100) if total_spent > 0 else 0

        entry = {
            "categoria": cat_name,
            "gastado": spent,
            "presupuesto": budget,
            "pct_of_total": round(pct_of_total, 1),
            "count": cat["count"],
        }

        if budget > 0:
            pct_used = spent / budget * 100
            entry["pct_usado"] = round(pct_used, 1)
            entry["restante"] = budget - spent
            if pct_used > 100:
                over_budget.append(entry)
            elif pct_used < 70:
                under_budget.append(entry)

        categories_analysis.append(entry)

    # Grade
    if total_budget > 0:
        global_pct = total_spent / total_budget * 100
        cats_with_budget = [c for c in categories_analysis if c.get("presupuesto", 0) > 0]
        cats_under = [c for c in cats_with_budget if c.get("pct_usado", 0) <= 100]
        score = len(cats_under) / len(cats_with_budget) * 100 if cats_with_budget else 50
    else:
        global_pct = 0
        score = 50

    if score >= 80:
        grade, grade_emoji = "A", "🏆"
    elif score >= 60:
        grade, grade_emoji = "B", "👍"
    elif score >= 40:
        grade, grade_emoji = "C", "⚠️"
    else:
        grade, grade_emoji = "D", "🔴"

    # Month label
    month_label = date_from.strftime("%B %Y").capitalize()

    # --- Build WhatsApp message ---
    lines = [f"📊 *Resumen de {month_label}*\n"]

    # Grade
    lines.append(f"{grade_emoji} Nota: *{grade}*\n")

    # Totals
    lines.append(f"💰 Total gastado: *{_fmt(total_spent)}*")
    if total_budget > 0:
        lines.append(f"📋 Presupuesto: {_fmt(total_budget)} ({global_pct:.0f}% usado)")
    lines.append(f"🧾 {tx_count} transacciones · Mayor: {_fmt(biggest)}")

    # vs previous month
    if prev_total > 0:
        diff = total_spent - prev_total
        diff_pct = (diff / prev_total * 100) if prev_total > 0 else 0
        if diff > 0:
            lines.append(f"📈 +{_fmt(diff)} ({diff_pct:+.0f}%) vs mes anterior")
        else:
            lines.append(f"📉 {_fmt(diff)} ({diff_pct:+.0f}%) vs mes anterior")

    # Top categories
    lines.append(f"\n*Top categorías:*")
    for i, cat in enumerate(categories_analysis[:5]):
        emoji_bar = "🟢" if cat.get("pct_usado", 0) <= 80 else "🟡" if cat.get("pct_usado", 0) <= 100 else "🔴"
        pct_text = f" ({cat['pct_usado']:.0f}% presup.)" if "pct_usado" in cat else ""
        lines.append(f"{emoji_bar} {cat['categoria']}: {_fmt(cat['gastado'])} ({cat['pct_of_total']:.0f}%){pct_text}")

    # Over budget alerts
    if over_budget:
        lines.append(f"\n🔴 *Te pasaste en:*")
        for cat in over_budget:
            exceso = cat["gastado"] - cat["presupuesto"]
            lines.append(f"  · {cat['categoria']}: +{_fmt(exceso)} ({cat['pct_usado']:.0f}%)")

    # Positive
    if under_budget:
        best = min(under_budget, key=lambda c: c.get("pct_usado", 100))
        lines.append(f"\n✨ Mejor controlada: *{best['categoria']}* ({best.get('pct_usado', 0):.0f}% del presupuesto)")

    # Avg daily
    days = (date_to - date_from).days + 1
    daily_avg = total_spent / days if days > 0 else 0
    lines.append(f"\n📅 Promedio diario: {_fmt(daily_avg)}")

    whatsapp_message = "\n".join(lines)

    return {
        "period": period,
        "month_label": month_label,
        "grade": grade,
        "total_spent": total_spent,
        "total_budget": total_budget,
        "global_pct": round(global_pct, 1),
        "tx_count": tx_count,
        "biggest_expense": biggest,
        "prev_month_total": prev_total,
        "categories": categories_analysis,
        "over_budget": over_budget,
        "under_budget": under_budget,
        "daily_avg": round(daily_avg, 2),
        "whatsapp_message": whatsapp_message,
    }
