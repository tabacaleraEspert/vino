from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.api.deps import set_sheets_context
from app.core.security import require_user
from app.sheets.catalog_service import (
    list_reglas as svc_list_reglas,
    create_regla as svc_create_regla,
    patch_regla_by_id as svc_patch_regla,
    delete_regla_by_id as svc_delete_regla,
)

router = APIRouter()


class MerchantRuleIn(BaseModel):
    merchantId: str
    categoryId: str
    subcategoryId: Optional[str] = None


class MerchantRulePatch(BaseModel):
    merchantId: Optional[str] = None
    categoryId: Optional[str] = None
    subcategoryId: Optional[str] = None


@router.get("")
def get_reglas(
    comercio: Optional[str] = Query(default=None),
    categoria_id: Optional[str] = Query(default=None),
    subcategoria_id: Optional[str] = Query(default=None),
    user: dict = Depends(require_user),
):
    set_sheets_context(user)
    return svc_list_reglas(
        comercio=comercio,
        categoria_id=categoria_id,
        subcategoria_id=subcategoria_id,
    )


@router.post("")
def post_regla(payload: MerchantRuleIn):
    """
    Crea regla de comercio en Sheets.
    merchantId se resuelve a Comercio (nombre) desde store.
    """
    try:
        created = svc_create_regla(
            merchant_id=payload.merchantId,
            category_id=payload.categoryId,
            subcategory_id=payload.subcategoryId,
        )
        return {
            "id": created["id"],
            "merchantId": payload.merchantId,
            "categoryId": created["categoria_id"],
            "subcategoryId": created["subcategoria_id"] or None,
        }
    except KeyError as e:
        msg = str(e).strip("'\"")
        raise HTTPException(status_code=404, detail=msg)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}")
def patch_regla(id: str, payload: MerchantRulePatch, user: dict = Depends(require_user)):
    set_sheets_context(user)
    try:
        patch = payload.model_dump(exclude_unset=True)
        svc_patch = {}
        if "categoryId" in patch:
            svc_patch["categoria_id"] = patch["categoryId"]
        if "subcategoryId" in patch:
            svc_patch["subcategoria_id"] = patch["subcategoryId"]
        if "merchantId" in patch:
            from app.sheets.catalog_service import _get_merchant_name
            name = _get_merchant_name(patch["merchantId"])
            if not name:
                raise HTTPException(status_code=404, detail="Comercio no encontrado")
            svc_patch["comercio"] = name
        if not svc_patch:
            from app.sheets.catalog_service import get_regla_by_id
            r = get_regla_by_id(id)
            if not r:
                raise HTTPException(status_code=404, detail="Regla no encontrada")
            return r
        updated = svc_patch_regla(id, svc_patch)
        return updated
    except KeyError as e:
        msg = str(e).strip("'\"")
        raise HTTPException(status_code=404, detail=msg or "Regla no encontrada")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}")
def delete_regla(id: str, user: dict = Depends(require_user)):
    set_sheets_context(user)
    if not svc_delete_regla(id):
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return {"deleted": True, "id": id}
