from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
def get_dashboard():
    return {
        "balance_mes": 0,
        "presupuesto_total": 0,
        "usado_pct": 0,
        "gastos_por_categoria": [],
        "transacciones_recientes": [],
    }
