"""
Format query results into WhatsApp-ready messages.

This is step 3 of the query pipeline (parse → execute → format).
Pure functions, no IO — easy to test.
"""
from __future__ import annotations

from app.services.query_executor import QueryResult
from app.services.query_parser import Metrica


def _fmt_money(amount: float, moneda: str = "ARS") -> str:
    """Format a money amount for WhatsApp."""
    formatted = f"${amount:,.0f}".replace(",", ".")
    if moneda != "ARS":
        formatted += f" {moneda}"
    return formatted


def _fmt_date(d) -> str:
    """Format a date as DD/MM."""
    if hasattr(d, "strftime"):
        return d.strftime("%d/%m")
    return str(d)


def format_query_result(result: QueryResult, user_name: str = "") -> str:
    """
    Format a QueryResult into a WhatsApp message.

    Returns a string ready to send via WhatsApp (with markdown bold/italic).
    """
    p = result.params
    moneda = p.moneda

    match result.metrica:
        case Metrica.TOTAL:
            return _format_total(result, moneda)
        case Metrica.PROMEDIO:
            return _format_promedio(result, moneda)
        case Metrica.MAYOR:
            return _format_mayor(result, moneda)
        case Metrica.MENOR:
            return _format_menor(result, moneda)
        case Metrica.TOP_N:
            return _format_top_n(result, moneda)
        case Metrica.PORCENTAJE:
            return _format_porcentaje(result, moneda)
        case Metrica.CONTEO:
            return _format_conteo(result, moneda)
        case Metrica.LISTADO:
            return _format_listado(result, moneda)
        case Metrica.RESUMEN:
            return _format_resumen(result, moneda)
        case Metrica.COMPARAR:
            return _format_comparar(result, moneda)
        case _:
            return "No pude armar la respuesta."


def _format_total(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    cat_label = f" en *{r.params.categorias[0]}*" if r.params.categorias else ""
    lines = [
        f"💰 *{_fmt_money(r.total, moneda)}*{cat_label} ({periodo})",
    ]
    if r.conteo:
        lines.append(f"📊 {r.conteo} gastos")
    return "\n".join(lines)


def _format_promedio(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    cat_label = f" en *{r.params.categorias[0]}*" if r.params.categorias else ""
    lines = [
        f"📊 Ticket promedio{cat_label}: *{_fmt_money(r.promedio, moneda)}* ({periodo})",
    ]
    if r.conteo:
        lines.append(f"Total: {_fmt_money(r.total, moneda)} en {r.conteo} gastos")
    return "\n".join(lines)


def _format_mayor(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    if r.movimientos:
        mov = r.movimientos[0]
        monto = float(mov.get("monto", 0))
        desc = mov.get("descripcion", "")
        fecha = _fmt_date(mov.get("fecha", ""))
        cat = mov.get("categoria_nombre", "")
        lines = [
            f"🔝 Mayor gasto ({periodo}):",
            f"*{_fmt_money(monto, moneda)}* — {desc}",
        ]
        if cat:
            lines.append(f"📂 {cat} · {fecha}")
    else:
        lines = [f"🔝 Mayor gasto ({periodo}): *{_fmt_money(r.mayor, moneda)}*"]
    return "\n".join(lines)


def _format_menor(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    if r.movimientos:
        mov = r.movimientos[0]
        monto = float(mov.get("monto", 0))
        desc = mov.get("descripcion", "")
        lines = [
            f"🔻 Menor gasto ({periodo}):",
            f"*{_fmt_money(monto, moneda)}* — {desc}",
        ]
    else:
        lines = [f"🔻 Menor gasto ({periodo}): *{_fmt_money(r.menor, moneda)}*"]
    return "\n".join(lines)


def _format_top_n(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    n = len(r.por_categoria)
    lines = [f"🏆 Top {n} categorías ({periodo}):"]
    for i, cat in enumerate(r.por_categoria, 1):
        lines.append(
            f"{i}. *{cat['categoria']}*: {_fmt_money(cat['total'], moneda)} "
            f"({cat['count']} gastos)"
        )
    if r.total:
        lines.append(f"\n💰 Total: *{_fmt_money(r.total, moneda)}*")
    return "\n".join(lines)


def _format_porcentaje(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    lines = [f"📊 Distribución por categoría ({periodo}):"]
    for cat in r.por_categoria:
        pct = (cat["total"] / r.total * 100) if r.total else 0
        lines.append(
            f"· *{cat['categoria']}*: {pct:.0f}% ({_fmt_money(cat['total'], moneda)})"
        )
    if r.total:
        lines.append(f"\n💰 Total: *{_fmt_money(r.total, moneda)}*")
    return "\n".join(lines)


def _format_conteo(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    cat_label = f" en *{r.params.categorias[0]}*" if r.params.categorias else ""
    lines = [f"🔢 *{r.conteo}* gastos{cat_label} ({periodo})"]
    if r.total:
        lines.append(f"💰 Total: {_fmt_money(r.total, moneda)}")
    return "\n".join(lines)


def _format_listado(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    cat_label = f" en {r.params.categorias[0]}" if r.params.categorias else ""
    total = r.total_movimientos
    shown = len(r.movimientos)
    lines = [f"📋 Últimos {shown} gastos{cat_label} ({periodo}):"]
    for mov in r.movimientos:
        monto = float(mov.get("monto", 0))
        desc = mov.get("descripcion", "")
        fecha = _fmt_date(mov.get("fecha", ""))
        cat = mov.get("categoria_nombre", "")
        line = f"· {fecha} — *{_fmt_money(monto, moneda)}* {desc}"
        if cat:
            line += f" ({cat})"
        lines.append(line)
    if total > shown:
        lines.append(f"\n_...y {total - shown} más_")
    return "\n".join(lines)


def _format_resumen(r: QueryResult, moneda: str) -> str:
    periodo = r.params.periodo_label
    lines = [f"📊 *Resumen {periodo}*"]
    lines.append(f"💰 Total gastado: *{_fmt_money(r.total, moneda)}*")
    lines.append(f"🔢 {r.conteo} gastos")
    if r.promedio:
        lines.append(f"📏 Ticket promedio: {_fmt_money(r.promedio, moneda)}")
    if r.mayor:
        lines.append(f"🔝 Mayor gasto: {_fmt_money(r.mayor, moneda)}")
    if r.por_categoria:
        lines.append("")
        lines.append("📂 *Por categoría:*")
        for cat in r.por_categoria:
            pct = (cat["total"] / r.total * 100) if r.total else 0
            lines.append(
                f"· {cat['categoria']}: {_fmt_money(cat['total'], moneda)} ({pct:.0f}%)"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _delta_pct(current: float, previous: float) -> float:
    """Percentage change from previous to current. Returns 0 if previous is 0."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100


def _delta_arrow(pct: float) -> str:
    """Arrow + formatted percentage."""
    if pct > 0:
        return f"📈 +{pct:.0f}%"
    elif pct < 0:
        return f"📉 {pct:.0f}%"
    else:
        return "➡️ 0%"


def _format_comparar(r: QueryResult, moneda: str) -> str:
    p = r.params
    label_a = p.periodo_label
    label_b = p.compare_periodo_label
    cat_label = f" en *{p.categorias[0]}*" if p.categorias else ""

    # Total comparison
    delta = _delta_pct(r.total, r.compare_total)
    diff_abs = r.total - r.compare_total
    arrow = _delta_arrow(delta)

    lines = [f"🔄 *Comparación{cat_label}*"]
    lines.append(f"*{label_a}*: {_fmt_money(r.total, moneda)} ({r.conteo} gastos)")
    lines.append(f"*{label_b}*: {_fmt_money(r.compare_total, moneda)} ({r.compare_conteo} gastos)")
    lines.append("")

    sign = "+" if diff_abs >= 0 else ""
    lines.append(f"💰 Diferencia: {sign}{_fmt_money(diff_abs, moneda)} ({arrow})")

    # Promedio comparison
    if r.promedio or r.compare_promedio:
        prom_delta = _delta_pct(r.promedio, r.compare_promedio)
        prom_arrow = _delta_arrow(prom_delta)
        lines.append(
            f"📏 Ticket promedio: {_fmt_money(r.promedio, moneda)} vs "
            f"{_fmt_money(r.compare_promedio, moneda)} ({prom_arrow})"
        )

    # Category breakdown comparison (only for general, non-category-filtered)
    if r.por_categoria and r.compare_por_categoria and not p.categorias:
        lines.append("")
        lines.append("📂 *Por categoría:*")
        # Build lookup for period B
        b_by_cat: dict[str, float] = {
            c["categoria"]: c["total"] for c in r.compare_por_categoria
        }
        for cat in r.por_categoria:
            name = cat["categoria"]
            total_a = cat["total"]
            total_b = b_by_cat.get(name, 0)
            cat_delta = _delta_pct(total_a, total_b)
            cat_arrow = _delta_arrow(cat_delta)
            lines.append(
                f"· {name}: {_fmt_money(total_a, moneda)} vs "
                f"{_fmt_money(total_b, moneda)} ({cat_arrow})"
            )

    return "\n".join(lines)
