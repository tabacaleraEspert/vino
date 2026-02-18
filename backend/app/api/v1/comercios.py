from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import set_sheets_context
from app.core.security import require_user
from app.storage.store import get_all, add_item, update_item, delete_item

router = APIRouter()

# Prefijo de comercios virtuales (derivados de transacciones, no creados explícitamente)
VIRTUAL_MERCHANT_PREFIX = "comercio-"


class MerchantIn(BaseModel):
    name: str
    defaultCategoryId: Optional[str] = None
    defaultSubcategoryId: Optional[str] = None


def _id_to_merchant_name(virtual_id: str) -> str:
    """Convierte comercio-ZENCITY_MARKET-ZENCITY -> ZENCITY MARKET ZENCITY"""
    if not virtual_id.startswith(VIRTUAL_MERCHANT_PREFIX):
        return virtual_id
    suffix = virtual_id[len(VIRTUAL_MERCHANT_PREFIX) :]
    return suffix.replace("_", " ")


@router.get("")
def list_comercios(user: dict = Depends(require_user)):
    return get_all("merchants")


@router.post("")
def create_comercio(payload: MerchantIn, user: dict = Depends(require_user)):
    return add_item("merchants", payload.model_dump())


@router.patch("/{id}")
def patch_comercio(id: str, payload: dict, user: dict = Depends(require_user)):
    set_sheets_context(user)
    updated = update_item("merchants", id, payload)
    if updated:
        return updated

    # Comercio virtual: existe en reglas (Sheets) pero no en store. Buscar por id (nombre derivado) y crear/actualizar.
    if id.startswith(VIRTUAL_MERCHANT_PREFIX):
        name = _id_to_merchant_name(id)
        cat_id = (payload.get("defaultCategoryId") or "").strip()
        sub_id = (payload.get("defaultSubcategoryId") or "").strip()
        if not cat_id:
            raise HTTPException(
                status_code=400,
                detail="Para comercios virtuales se requiere defaultCategoryId",
            )
        try:
            from app.sheets.catalog_service import (
                create_regla,
                list_reglas,
                patch_regla_by_id,
            )

            def _nombre_normalizado(s: str) -> str:
                return " ".join(str(s or "").strip().lower().split())

            name_norm = _nombre_normalizado(name)
            all_reglas = list_reglas(comercio=name)
            existing = [
                r
                for r in all_reglas
                if _nombre_normalizado(r.get("comercio", "")) == name_norm
            ]
            if existing:
                patch_regla_by_id(
                    existing[0]["id"],
                    {"categoria_id": cat_id, "subcategoria_id": sub_id or ""},
                )
            else:
                create_regla(
                    merchant_id=id,
                    category_id=cat_id,
                    subcategory_id=sub_id or "",
                    merchant_name=name,
                )
        except KeyError as e:
            msg = str(e).strip("'\"")
            raise HTTPException(status_code=404, detail=msg)
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))

        new_merchant = add_item(
            "merchants",
            {
                "name": name,
                "defaultCategoryId": cat_id,
                "defaultSubcategoryId": sub_id or None,
            },
            custom_id=id,
        )
        return new_merchant

    raise HTTPException(status_code=404, detail="Comercio no encontrado")


@router.delete("/{id}")
def delete_comercio(id: str, user: dict = Depends(require_user)):
    if not delete_item("merchants", id):
        raise HTTPException(status_code=404, detail="Comercio no encontrado")
    return {"deleted": True, "id": id}
