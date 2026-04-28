"""
Execute a parsed financial query against the database.

Takes QueryParams from query_parser and calls the right repo functions.
This is step 2 of the query pipeline (parse → execute → format).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import movimiento_agg as agg
from app.repositories.movimiento_repo import list_movimientos
from app.services.query_parser import Metrica, QueryParams

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Raw results from executing a financial query."""
    metrica: Metrica
    params: QueryParams
    # Populated depending on metrica:
    total: float = 0.0
    promedio: float = 0.0
    conteo: int = 0
    mayor: float = 0.0
    menor: float = 0.0
    por_categoria: list[dict[str, Any]] = field(default_factory=list)
    movimientos: list[dict[str, Any]] = field(default_factory=list)
    total_movimientos: int = 0
    # For COMPARAR:
    compare_total: float = 0.0
    compare_conteo: int = 0
    compare_promedio: float = 0.0
    compare_por_categoria: list[dict[str, Any]] = field(default_factory=list)


async def execute_query(
    db: AsyncSession,
    user_id: int,
    params: QueryParams,
) -> QueryResult:
    """
    Execute the right DB queries based on the parsed QueryParams.

    Each metrica maps to specific repo calls. RESUMEN runs multiple
    queries to build a complete picture.
    """
    result = QueryResult(metrica=params.metrica, params=params)
    cat_id = params.categoria_ids[0] if params.categoria_ids else None

    match params.metrica:
        case Metrica.TOTAL:
            if cat_id:
                rows = await agg.avg_ticket_por_categoria(
                    db, user_id, params.from_date, params.to_date,
                    id_categoria=cat_id, moneda=params.moneda,
                )
                result.total = rows[0]["total"] if rows else 0.0
                result.conteo = rows[0]["count"] if rows else 0
            else:
                result.total = await agg.sum_gastos_mes(
                    db, user_id, params.from_date, params.to_date,
                    moneda=params.moneda,
                )
                result.conteo = await agg.count_gastos_mes(
                    db, user_id, params.from_date, params.to_date,
                    moneda=params.moneda,
                )

        case Metrica.PROMEDIO:
            rows = await agg.avg_ticket_por_categoria(
                db, user_id, params.from_date, params.to_date,
                id_categoria=cat_id, moneda=params.moneda,
            )
            if rows:
                if cat_id:
                    result.promedio = rows[0]["avg_ticket"]
                    result.conteo = rows[0]["count"]
                    result.total = rows[0]["total"]
                else:
                    total_sum = sum(r["total"] for r in rows)
                    total_count = sum(r["count"] for r in rows)
                    result.promedio = total_sum / total_count if total_count else 0
                    result.conteo = total_count
                    result.total = total_sum

        case Metrica.MAYOR:
            # Get the single largest expense
            result.mayor = await agg.mayor_gasto_mes(
                db, user_id, params.from_date, params.to_date,
                moneda=params.moneda,
            )
            # Also get the actual transaction for context
            movs, _ = await list_movimientos(
                db, user_id,
                from_date=params.from_date, to_date=params.to_date,
                tipo="Gasto", moneda=params.moneda,
                categoria_id=cat_id,
                limit=1, offset=0,
            )
            result.movimientos = movs

        case Metrica.MENOR:
            # Get smallest — list sorted ascending, take first
            movs, total = await list_movimientos(
                db, user_id,
                from_date=params.from_date, to_date=params.to_date,
                tipo="Gasto", moneda=params.moneda,
                categoria_id=cat_id,
                min_amount=0.01,  # exclude zero
                limit=1, offset=0,
            )
            if movs:
                result.menor = float(movs[0].get("monto", 0))
                result.movimientos = movs

        case Metrica.TOP_N | Metrica.PORCENTAJE:
            result.por_categoria = await agg.gastos_por_categoria(
                db, user_id, params.from_date, params.to_date,
                moneda=params.moneda, top=params.top_n,
            )
            result.total = await agg.sum_gastos_mes(
                db, user_id, params.from_date, params.to_date,
                moneda=params.moneda,
            )

        case Metrica.CONTEO:
            if cat_id:
                rows = await agg.avg_ticket_por_categoria(
                    db, user_id, params.from_date, params.to_date,
                    id_categoria=cat_id, moneda=params.moneda,
                )
                result.conteo = rows[0]["count"] if rows else 0
                result.total = rows[0]["total"] if rows else 0.0
            else:
                result.conteo = await agg.count_gastos_mes(
                    db, user_id, params.from_date, params.to_date,
                    moneda=params.moneda,
                )

        case Metrica.LISTADO:
            movs, total = await list_movimientos(
                db, user_id,
                from_date=params.from_date, to_date=params.to_date,
                tipo="Gasto", moneda=params.moneda,
                categoria_id=cat_id,
                limit=params.top_n, offset=0,
            )
            result.movimientos = movs
            result.total_movimientos = total

        case Metrica.RESUMEN:
            # Run multiple queries for a complete picture
            result.total = await agg.sum_gastos_mes(
                db, user_id, params.from_date, params.to_date,
                moneda=params.moneda,
            )
            result.conteo = await agg.count_gastos_mes(
                db, user_id, params.from_date, params.to_date,
                moneda=params.moneda,
            )
            result.por_categoria = await agg.gastos_por_categoria(
                db, user_id, params.from_date, params.to_date,
                moneda=params.moneda, top=5,
            )
            result.mayor = await agg.mayor_gasto_mes(
                db, user_id, params.from_date, params.to_date,
                moneda=params.moneda,
            )
            if result.conteo > 0:
                result.promedio = result.total / result.conteo

        case Metrica.COMPARAR:
            if not params.compare_from_date or not params.compare_to_date:
                # Fallback: can't compare without second period
                result.metrica = Metrica.RESUMEN
                return await execute_query(db, user_id, params)

            # Period A (primary)
            if cat_id:
                rows_a = await agg.avg_ticket_por_categoria(
                    db, user_id, params.from_date, params.to_date,
                    id_categoria=cat_id, moneda=params.moneda,
                )
                result.total = rows_a[0]["total"] if rows_a else 0.0
                result.conteo = rows_a[0]["count"] if rows_a else 0
                result.promedio = rows_a[0]["avg_ticket"] if rows_a else 0.0
            else:
                result.total = await agg.sum_gastos_mes(
                    db, user_id, params.from_date, params.to_date,
                    moneda=params.moneda,
                )
                result.conteo = await agg.count_gastos_mes(
                    db, user_id, params.from_date, params.to_date,
                    moneda=params.moneda,
                )
                if result.conteo > 0:
                    result.promedio = result.total / result.conteo

            # Period B (comparison)
            if cat_id:
                rows_b = await agg.avg_ticket_por_categoria(
                    db, user_id, params.compare_from_date, params.compare_to_date,
                    id_categoria=cat_id, moneda=params.moneda,
                )
                result.compare_total = rows_b[0]["total"] if rows_b else 0.0
                result.compare_conteo = rows_b[0]["count"] if rows_b else 0
                result.compare_promedio = rows_b[0]["avg_ticket"] if rows_b else 0.0
            else:
                result.compare_total = await agg.sum_gastos_mes(
                    db, user_id, params.compare_from_date, params.compare_to_date,
                    moneda=params.moneda,
                )
                result.compare_conteo = await agg.count_gastos_mes(
                    db, user_id, params.compare_from_date, params.compare_to_date,
                    moneda=params.moneda,
                )
                if result.compare_conteo > 0:
                    result.compare_promedio = result.compare_total / result.compare_conteo

            # Category breakdown for both periods (general comparison)
            if not cat_id:
                result.por_categoria = await agg.gastos_por_categoria(
                    db, user_id, params.from_date, params.to_date,
                    moneda=params.moneda, top=params.top_n,
                )
                result.compare_por_categoria = await agg.gastos_por_categoria(
                    db, user_id, params.compare_from_date, params.compare_to_date,
                    moneda=params.moneda, top=params.top_n,
                )

    return result
