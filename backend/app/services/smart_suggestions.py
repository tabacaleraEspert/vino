"""Smart Suggestions Engine — context-aware financial advice after every expense."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.movimiento_agg import (
    avg_ticket_por_categoria,
    gastos_categoria_por_periodo,
    gastos_por_dia_semana,
    sum_gastos_mes,
)
from app.repositories.presupuesto_repo import list_presupuestos
from app.utils.parse_utils import parse_period

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class SuggestionType(str, Enum):
    BUDGET_STATUS = "budget_status"
    PACE_WARNING = "pace_warning"
    OVERSPENT = "overspent"
    POSITIVE = "positive"
    NO_BUDGET = "no_budget"
    RELATIVE_VALUE = "relative_value"
    BEHAVIORAL = "behavioral"
    PROACTIVE_ALERT = "proactive_alert"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    POSITIVE = "positive"


@dataclass
class CategoryMetrics:
    categoria_id: int
    categoria_nombre: str
    presupuesto: float
    gastado: float
    restante: float
    pct_usado: float
    avg_ticket: float
    min_ticket: float
    max_ticket: float
    tx_count: int
    trend_vs_last_month: float | None  # % change, None if no prior data


@dataclass
class MonthContext:
    today: date
    days_in_month: int
    days_elapsed: int
    days_remaining: int
    pct_month_elapsed: float  # 0-100


@dataclass
class Suggestion:
    tipo: SuggestionType
    severity: Severity
    categoria: str
    mensaje: str
    mensaje_whatsapp: str
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(n: float) -> str:
    """Format number as Argentine currency without decimals."""
    return f"${n:,.0f}".replace(",", ".")


def compute_month_context(period: str) -> MonthContext:
    """Pure computation: day-of-month progress."""
    date_from, date_to = parse_period(period)
    today = date.today()
    days_in_month = (date_to - date_from).days + 1

    if today < date_from:
        days_elapsed = 0
    elif today > date_to:
        days_elapsed = days_in_month
    else:
        days_elapsed = (today - date_from).days + 1

    days_remaining = max(0, days_in_month - days_elapsed)
    pct = round(days_elapsed / days_in_month * 100, 1) if days_in_month > 0 else 100

    return MonthContext(
        today=today,
        days_in_month=days_in_month,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        pct_month_elapsed=pct,
    )


async def compute_category_metrics(
    db: AsyncSession,
    id_usuario: int,
    id_categoria: int,
    period: str,
    moneda: str = "ARS",
) -> CategoryMetrics:
    """Full metrics for a single category: budget, spent, avg ticket, trend."""
    date_from, date_to = parse_period(period)
    periodo_mes = date(date_from.year, date_from.month, 1)

    # Budget
    presup_rows = await list_presupuestos(db, id_usuario, periodo_mes=periodo_mes)
    presupuesto = 0.0
    cat_nombre = ""
    for p in presup_rows:
        if str(p.get("categoria_id", "")) == str(id_categoria):
            presupuesto += float(p.get("monto", 0))
            cat_nombre = p.get("categoria_nombre", "")

    # Spent + avg ticket (single query)
    tickets = await avg_ticket_por_categoria(
        db, id_usuario, date_from, date_to, id_categoria=id_categoria, moneda=moneda
    )
    if tickets:
        t = tickets[0]
        gastado = t["total"]
        avg_ticket = t["avg_ticket"]
        min_ticket = t["min_ticket"]
        max_ticket = t["max_ticket"]
        tx_count = t["count"]
        if not cat_nombre:
            cat_nombre = t["categoria"]
    else:
        gastado = 0
        avg_ticket = 0
        min_ticket = 0
        max_ticket = 0
        tx_count = 0

    # Trend: compare with last month
    trend = None
    try:
        history = await gastos_categoria_por_periodo(db, id_usuario, id_categoria, months_back=2, moneda=moneda)
        if len(history) >= 2:
            prev = history[-2]["total"]
            curr = history[-1]["total"]
            if prev > 0:
                trend = round((curr - prev) / prev * 100, 1)
    except Exception:
        pass

    restante = presupuesto - gastado
    pct_usado = round(gastado / presupuesto * 100, 1) if presupuesto > 0 else 0

    return CategoryMetrics(
        categoria_id=id_categoria,
        categoria_nombre=cat_nombre or "Sin categoría",
        presupuesto=presupuesto,
        gastado=gastado,
        restante=restante,
        pct_usado=pct_usado,
        avg_ticket=avg_ticket,
        min_ticket=min_ticket,
        max_ticket=max_ticket,
        tx_count=tx_count,
        trend_vs_last_month=trend,
    )


# ---------------------------------------------------------------------------
# Post-expense suggestions (called after every expense registration)
# ---------------------------------------------------------------------------

async def post_expense_suggestions(
    db: AsyncSession,
    id_usuario: int,
    id_categoria: int,
    monto: float,
    period: str,
    moneda: str = "ARS",
) -> list[Suggestion]:
    """
    Generate 1-2 suggestions to append to the WhatsApp confirmation.
    Called immediately after registering an expense.
    """
    suggestions: list[Suggestion] = []

    try:
        metrics = await compute_category_metrics(db, id_usuario, id_categoria, period, moneda)
        ctx = compute_month_context(period)
    except Exception as e:
        logger.warning("Failed to compute metrics for suggestions: %s", e)
        return []

    cat = metrics.categoria_nombre

    # --- 1. BUDGET STATUS (always, if budget exists) ---
    if metrics.presupuesto > 0:
        if metrics.pct_usado > 100:
            exceso = metrics.gastado - metrics.presupuesto
            suggestions.append(Suggestion(
                tipo=SuggestionType.OVERSPENT,
                severity=Severity.CRITICAL,
                categoria=cat,
                mensaje=f"{cat}: superaste el presupuesto por {_fmt(exceso)}",
                mensaje_whatsapp=f"🔴 {cat}: {_fmt(metrics.gastado)}/{_fmt(metrics.presupuesto)} ({metrics.pct_usado:.0f}%) · superaste por {_fmt(exceso)}",
                data={"pct_usado": metrics.pct_usado, "exceso": exceso},
            ))
        else:
            emoji = "📊"
            suggestions.append(Suggestion(
                tipo=SuggestionType.BUDGET_STATUS,
                severity=Severity.INFO,
                categoria=cat,
                mensaje=f"{cat}: {_fmt(metrics.gastado)} de {_fmt(metrics.presupuesto)} ({metrics.pct_usado:.0f}%) — {ctx.days_remaining} días restantes",
                mensaje_whatsapp=f"{emoji} {cat}: {_fmt(metrics.gastado)}/{_fmt(metrics.presupuesto)} ({metrics.pct_usado:.0f}%) · {ctx.days_remaining} días restantes",
                data={"pct_usado": metrics.pct_usado, "restante": metrics.restante, "days_remaining": ctx.days_remaining},
            ))

        # --- 2. PACE WARNING ---
        if ctx.pct_month_elapsed > 15 and metrics.pct_usado > 0:
            pace_ratio = metrics.pct_usado / ctx.pct_month_elapsed
            if pace_ratio > 1.15 and metrics.pct_usado < 100:
                projected = (metrics.gastado / ctx.days_elapsed * ctx.days_in_month) if ctx.days_elapsed > 0 else 0
                if projected > metrics.presupuesto:
                    suggestions.append(Suggestion(
                        tipo=SuggestionType.PACE_WARNING,
                        severity=Severity.WARNING,
                        categoria=cat,
                        mensaje=f"A este ritmo vas a gastar ~{_fmt(projected)} (presupuesto: {_fmt(metrics.presupuesto)})",
                        mensaje_whatsapp=f"⚠️ Ritmo alto: a este paso llegarías a ~{_fmt(projected)}",
                        data={"projected": projected, "pace_ratio": round(pace_ratio, 2)},
                    ))

        # --- 3. POSITIVE ---
        if ctx.days_elapsed > ctx.days_in_month / 2 and metrics.pct_usado < ctx.pct_month_elapsed * 0.7 and metrics.pct_usado < 60:
            suggestions.append(Suggestion(
                tipo=SuggestionType.POSITIVE,
                severity=Severity.POSITIVE,
                categoria=cat,
                mensaje=f"Venís bien en {cat}, te sobra margen",
                mensaje_whatsapp=f"✨ Venís bien en {cat}, te sobra margen",
                data={},
            ))

    else:
        # No budget
        suggestions.append(Suggestion(
            tipo=SuggestionType.NO_BUDGET,
            severity=Severity.INFO,
            categoria=cat,
            mensaje=f"No tenés presupuesto para {cat}. Considerá definir uno.",
            mensaje_whatsapp=f"💡 Sin presupuesto en {cat}. Definí uno desde la app.",
            data={},
        ))

    # --- 4. RELATIVE VALUE (is this expensive for you?) ---
    if metrics.avg_ticket > 0 and metrics.tx_count >= 3:
        ratio = monto / metrics.avg_ticket
        if ratio >= 2.5:
            suggestions.append(Suggestion(
                tipo=SuggestionType.RELATIVE_VALUE,
                severity=Severity.INFO,
                categoria=cat,
                mensaje=f"Este gasto ({_fmt(monto)}) es {ratio:.1f}x tu promedio en {cat} ({_fmt(metrics.avg_ticket)})",
                mensaje_whatsapp=f"💡 Este gasto es {ratio:.1f}x tu promedio en {cat} ({_fmt(metrics.avg_ticket)})",
                data={"ratio": round(ratio, 1), "avg_ticket": metrics.avg_ticket},
            ))

    # --- 5. TREND WARNING ---
    if metrics.trend_vs_last_month is not None and metrics.trend_vs_last_month > 30:
        suggestions.append(Suggestion(
            tipo=SuggestionType.BEHAVIORAL,
            severity=Severity.WARNING,
            categoria=cat,
            mensaje=f"Tu gasto en {cat} subió {metrics.trend_vs_last_month:.0f}% vs el mes pasado",
            mensaje_whatsapp=f"📈 {cat} subió {metrics.trend_vs_last_month:.0f}% vs mes pasado",
            data={"trend": metrics.trend_vs_last_month},
        ))

    # Sort by severity and return max 2
    priority = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2, Severity.POSITIVE: 3}
    suggestions.sort(key=lambda s: priority.get(s.severity, 9))

    # Always keep BUDGET_STATUS/OVERSPENT as first, then the most important other one
    result = []
    budget_sug = next((s for s in suggestions if s.tipo in (SuggestionType.BUDGET_STATUS, SuggestionType.OVERSPENT, SuggestionType.NO_BUDGET)), None)
    if budget_sug:
        result.append(budget_sug)
    other = [s for s in suggestions if s not in result]
    if other:
        result.append(other[0])

    return result
