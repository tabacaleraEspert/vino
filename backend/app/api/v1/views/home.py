from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.deps import set_sheets_context
from app.core.security import require_user
from app.views.home_service import get_home_summary as svc_get_home_summary
from app.views.home_service import get_home_breakdown as svc_get_home_breakdown

router = APIRouter()


@router.get("/summary")
def get_home_summary(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2025-10"),
    moneda: str = Query(default="ARS"),
    user: dict = Depends(require_user),
):
    """
    Resumen para la tarjeta de Inicio: gasto del mes y presupuesto.
    user_id viene del JWT (id del usuario en MaestroUsuarios).
    """
    set_sheets_context(user)
    try:
        return svc_get_home_summary(
            period=period, user_id=user["sub"], moneda=moneda
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/breakdown")
def get_home_breakdown(
    period: str = Query(..., description="Formato YYYY-MM, ej: 2026-02"),
    currency: str = Query(default="ARS"),
    top_categories: int = Query(default=6, ge=1, le=20),
    recent_limit: int = Query(default=5, ge=1, le=50),
    include_zeros: bool = Query(default=False),
    user: dict = Depends(require_user),
):
    """
    Gastos por categoría (top N), transacciones recientes, mayor_gasto, transacciones_count.
    user_id viene del JWT (id del usuario en MaestroUsuarios).
    """
    set_sheets_context(user)
    try:
        return svc_get_home_breakdown(
            period=period,
            user_id=user["sub"],
            currency=currency,
            top_categories=top_categories,
            recent_limit=recent_limit,
            include_zeros=include_zeros,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
