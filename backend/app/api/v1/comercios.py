from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import set_sheets_context
from app.core.security import require_user
from app.db.catalog import _get_id_usuario
from app.db.regla_comercio import list_reglas_comercio, create_regla_user, update_regla
from app.utils.normalize import normalize_text
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
def patch_comercio(id: str, payload: dict, background_tasks: BackgroundTasks, user: dict = Depends(require_user)):
    set_sheets_context(user)
    updated = update_item("merchants", id, payload)
    if updated:
        return updated

    # Comercio virtual: existe en reglas (SQL ReglaComercio) pero no en store.
    if id.startswith(VIRTUAL_MERCHANT_PREFIX):
        name = _id_to_merchant_name(id)
        cat_id = (payload.get("defaultCategoryId") or "").strip()
        sub_id = (payload.get("defaultSubcategoryId") or "").strip()
        if not sub_id:
            sub_id = cat_id
        if not sub_id:
            raise HTTPException(
                status_code=400,
                detail="Para comercios virtuales se requiere defaultSubcategoryId o defaultCategoryId",
            )
        try:
            id_usuario = _get_id_usuario(user)
            name_norm = normalize_text(name)
            all_reglas = list_reglas_comercio(id_usuario)
            existing = [
                r for r in all_reglas
                if normalize_text(r.get("comercio", r.get("patron", ""))) == name_norm
            ]
            regla_cat_id = cat_id
            regla_sub_id = sub_id
            if existing:
                updated = update_regla(
                    id_usuario=id_usuario,
                    regla_id=existing[0]["id"],
                    id_subcategoria=sub_id,
                )
                if updated:
                    regla_cat_id = updated.get("categoria_id", cat_id)
                    regla_sub_id = updated.get("subcategoria_id", sub_id)
                    from app.services.recategorizacion import enqueue_recategorization_job, process_job
                    job = enqueue_recategorization_job(id_usuario, int(updated["id"]), days_back=30)
                    background_tasks.add_task(process_job, id_usuario, job["id"])
            else:
                created = create_regla_user(
                    id_usuario=id_usuario,
                    patron=name,
                    id_subcategoria=sub_id,
                )
                regla_cat_id = created.get("categoria_id", cat_id)
                regla_sub_id = created.get("subcategoria_id", sub_id)
        except KeyError as e:
            msg = str(e).strip("'\"")
            raise HTTPException(status_code=404, detail=msg)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        new_merchant = add_item(
            "merchants",
            {
                "name": name,
                "defaultCategoryId": regla_cat_id or cat_id,
                "defaultSubcategoryId": regla_sub_id or None,
            },
            custom_id=id,
        )
        if existing and "recategorization_job_id" not in new_merchant:
            new_merchant["recategorization_job_id"] = job["id"]
        return new_merchant

    raise HTTPException(status_code=404, detail="Comercio no encontrado")


@router.delete("/{id}")
def delete_comercio(id: str, user: dict = Depends(require_user)):
    if not delete_item("merchants", id):
        raise HTTPException(status_code=404, detail="Comercio no encontrado")
    return {"deleted": True, "id": id}
