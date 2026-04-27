"""Budget analysis views: budget vs actual + smart suggestions."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.services.presupuesto_analysis import budget_vs_actual, generate_suggestions

router = APIRouter()


@router.get("/status")
async def get_budget_status(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2026-04"),
    moneda: str = Query(default="ARS"),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Presupuesto vs gasto real por categoría.

    Devuelve por cada categoría: presupuesto, gastado, restante, % usado.
    Incluye categorías sin presupuesto que tienen gastos.
    """
    try:
        return await budget_vs_actual(db, id_usuario, period, moneda)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/suggestions")
async def get_budget_suggestions(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2026-04"),
    moneda: str = Query(default="ARS"),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Sugerencias financieras inteligentes basadas en presupuesto vs gasto.

    Tipos: alerta (pasaste), advertencia (cerca del límite), info, positivo.
    """
    try:
        suggestions = await generate_suggestions(db, id_usuario, period, moneda)
        return {"period": period, "moneda": moneda, "suggestions": suggestions}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/monthly-summary")
async def get_monthly_summary(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2026-04"),
    moneda: str = Query(default="ARS"),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Resumen completo del mes: nota, totales, top categorías,
    comparación con mes anterior, alertas de presupuesto.
    """
    from app.services.monthly_summary import generate_monthly_summary
    try:
        return await generate_monthly_summary(db, id_usuario, period, moneda)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
