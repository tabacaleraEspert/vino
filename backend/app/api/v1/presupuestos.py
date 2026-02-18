from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import set_sheets_context
from app.core.security import require_user
from app.sheets.catalog_service import (
    list_presupuestos as svc_list_presupuestos,
    create_presupuesto as svc_create_presupuesto,
    patch_presupuesto_by_id as svc_patch_presupuesto,
    delete_presupuesto_by_id as svc_delete_presupuesto,
)
from pydantic import BaseModel
from typing import Literal, Optional

router = APIRouter()


class BudgetIn(BaseModel):
    categoryId: str
    subcategoryId: Optional[str] = None
    mes_anio: Optional[str] = None
    amount: float
    period: Literal["monthly", "weekly", "yearly"] = "monthly"
    spent: float = 0


class BudgetPatch(BaseModel):
    categoryId: Optional[str] = None
    subcategoryId: Optional[str] = None
    mes_anio: Optional[str] = None
    amount: Optional[float] = None


@router.get("")
def get_presupuestos(
    mes_anio: Optional[str] = Query(default=None),
    categoria_id: Optional[str] = Query(default=None),
    subcategoria_id: Optional[str] = Query(default=None),
    user: dict = Depends(require_user),
):
    set_sheets_context(user)
    return svc_list_presupuestos(
        mes_anio=mes_anio,
        categoria_id=categoria_id,
        subcategoria_id=subcategoria_id,
    )


@router.post("")
def post_presupuesto(payload: BudgetIn, user: dict = Depends(require_user)):
    """
    Crea presupuesto en Sheets.
    subcategoryId vacío = presupuesto para toda la categoría (general).
    mes_anio opcional; si no viene, usa mes actual.
    """
    set_sheets_context(user)
    try:
        created = svc_create_presupuesto(
            mes_anio=payload.mes_anio or "",
            categoria_id=payload.categoryId,
            subcategoria_id=payload.subcategoryId,
            monto=payload.amount,
        )
        return {
            "id": created["id"],
            "categoryId": created["categoria_id"],
            "subcategoryId": created["subcategoria_id"] or None,
            "mes_anio": created["mes_anio"],
            "amount": float(created["monto"].replace(",", "")) if created.get("monto") else 0,
            "period": payload.period,
            "spent": payload.spent,
        }
    except KeyError as e:
        msg = str(e).strip("'\"")
        raise HTTPException(status_code=404, detail=msg)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}")
def patch_presupuesto(id: str, payload: BudgetPatch, user: dict = Depends(require_user)):
    set_sheets_context(user)
    try:
        patch = payload.model_dump(exclude_unset=True)
        svc_patch = {}
        if "categoryId" in patch:
            svc_patch["categoria_id"] = patch["categoryId"]
        if "subcategoryId" in patch:
            svc_patch["subcategoria_id"] = patch["subcategoryId"]
        if "mes_anio" in patch:
            svc_patch["mes_anio"] = patch["mes_anio"]
        if "amount" in patch:
            svc_patch["monto"] = patch["amount"]
        if not svc_patch:
            from app.sheets.catalog_service import get_presupuesto_by_id
            p = get_presupuesto_by_id(id)
            if not p:
                raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
            return p
        updated = svc_patch_presupuesto(id, svc_patch)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}")
def delete_presupuesto(id: str, user: dict = Depends(require_user)):
    set_sheets_context(user)
    if not svc_delete_presupuesto(id):
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return {"deleted": True, "id": id}
