from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import set_sheets_context
from app.cache.sql_catalog_cache import invalidate
from app.core.security import require_user
from app.db.catalog import _get_id_usuario
from app.db.comercios import (
    list_comercios_sql,
    create_comercio_sql,
    update_comercio_sql,
    delete_comercio_sql,
    get_comercio_by_id_sql,
)
from app.db.regla_comercio import list_reglas_comercio, create_regla_user, update_regla
from app.utils.normalize import normalize_text

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
    id_usuario = _get_id_usuario(user)
    return list_comercios_sql(id_usuario)


@router.post("")
def create_comercio(payload: MerchantIn, user: dict = Depends(require_user)):
    id_usuario = _get_id_usuario(user)
    try:
        created = create_comercio_sql(
            id_usuario=id_usuario,
            nombre=payload.name,
            default_category_id=payload.defaultCategoryId,
            default_subcategory_id=payload.defaultSubcategoryId,
        )
        invalidate(id_usuario)
        return created
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}")
def patch_comercio(id: str, payload: dict, background_tasks: BackgroundTasks, user: dict = Depends(require_user)):
    set_sheets_context(user)
    id_usuario = _get_id_usuario(user)
    cat_id = (payload.get("defaultCategoryId") or "").strip()
    sub_id = (payload.get("defaultSubcategoryId") or "").strip()
    if not sub_id and cat_id:
        from app.db.catalog import list_subcategorias_sql
        subs = list_subcategorias_sql(id_usuario, categoria_id=int(cat_id))
        sub_id = str(subs[0]["id"]) if subs else ""

    # Comercio existente en SQL
    existing = get_comercio_by_id_sql(id_usuario, id)
    if existing:
        try:
            updated = update_comercio_sql(
                id_usuario=id_usuario,
                comercio_id=id,
                nombre=payload.get("name"),
                default_category_id=cat_id or None,
                default_subcategory_id=sub_id or None,
            )
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e).strip("'\""))
        if not updated:
            raise HTTPException(status_code=404, detail="Comercio no encontrado")
        # Sincronizar ReglaComercio y recategorizar si hay cat/sub
        if cat_id or sub_id:
            try:
                name = (updated.get("name") or "").strip()
                if sub_id and name:
                    name_norm = normalize_text(name)
                    all_reglas = list_reglas_comercio(id_usuario)
                    regla_match = [
                        r for r in all_reglas
                        if normalize_text(r.get("comercio", r.get("patron", ""))) == name_norm
                    ]
                    if regla_match:
                        regla_updated = update_regla(
                            id_usuario=id_usuario,
                            regla_id=regla_match[0]["id"],
                            id_subcategoria=sub_id,
                        )
                        if regla_updated:
                            invalidate(id_usuario)
                            from app.services.recategorizacion import enqueue_recategorization_job, process_job
                            job = enqueue_recategorization_job(id_usuario, int(regla_updated["id"]), days_back=365)
                            background_tasks.add_task(process_job, id_usuario, job["id"])
                            updated["recategorization_job_id"] = job["id"]
                    else:
                        created = create_regla_user(
                            id_usuario=id_usuario,
                            patron=name,
                            id_subcategoria=sub_id,
                        )
                        invalidate(id_usuario)
                        from app.services.recategorizacion import enqueue_recategorization_job, process_job
                        job = enqueue_recategorization_job(id_usuario, int(created["id"]), days_back=365)
                        background_tasks.add_task(process_job, id_usuario, job["id"])
                        updated["recategorization_job_id"] = job["id"]
            except (ValueError, KeyError):
                pass
        return updated

    # Comercio virtual: existe en reglas pero no en tabla Comercio
    if id.startswith(VIRTUAL_MERCHANT_PREFIX):
        name = _id_to_merchant_name(id)
        if not sub_id:
            sub_id = cat_id
        if not sub_id:
            raise HTTPException(
                status_code=400,
                detail="Para comercios virtuales se requiere defaultSubcategoryId o defaultCategoryId",
            )
        try:
            name_norm = normalize_text(name)
            all_reglas = list_reglas_comercio(id_usuario)
            regla_match = [
                r for r in all_reglas
                if normalize_text(r.get("comercio", r.get("patron", ""))) == name_norm
            ]
            regla_cat_id = cat_id
            regla_sub_id = sub_id
            job = None
            if regla_match:
                regla_updated = update_regla(
                    id_usuario=id_usuario,
                    regla_id=regla_match[0]["id"],
                    id_subcategoria=sub_id,
                )
                if regla_updated:
                    invalidate(id_usuario)
                    from app.services.recategorizacion import enqueue_recategorization_job, process_job
                    job = enqueue_recategorization_job(id_usuario, int(regla_updated["id"]), days_back=30)
                    background_tasks.add_task(process_job, id_usuario, job["id"])
                    result = {
                        "id": str(regla_updated["id"]),
                        "name": (regla_updated.get("comercio") or regla_updated.get("patron") or "").strip(),
                        "defaultCategoryId": str(regla_updated["categoria_id"]) if regla_updated.get("categoria_id") else None,
                        "defaultSubcategoryId": str(regla_updated["subcategoria_id"]) if regla_updated.get("subcategoria_id") else None,
                    }
                    if job:
                        result["recategorization_job_id"] = job["id"]
                    return result
            else:
                created = create_regla_user(
                    id_usuario=id_usuario,
                    patron=name,
                    id_subcategoria=sub_id,
                )
                invalidate(id_usuario)
                from app.services.recategorizacion import enqueue_recategorization_job, process_job
                job = enqueue_recategorization_job(id_usuario, int(created["id"]), days_back=365)
                background_tasks.add_task(process_job, id_usuario, job["id"])
                return {
                    "id": str(created["id"]),
                    "name": (created.get("comercio") or created.get("patron") or "").strip(),
                    "defaultCategoryId": str(created["categoria_id"]) if created.get("categoria_id") else None,
                    "defaultSubcategoryId": str(created["subcategoria_id"]) if created.get("subcategoria_id") else None,
                    "recategorization_job_id": job["id"],
                }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e).strip("'\""))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    raise HTTPException(status_code=404, detail="Comercio no encontrado")


@router.delete("/{id}")
def delete_comercio(id: str, user: dict = Depends(require_user)):
    id_usuario = _get_id_usuario(user)
    if not delete_comercio_sql(id_usuario, id):
        raise HTTPException(status_code=404, detail="Comercio no encontrado")
    invalidate(id_usuario)
    return {"deleted": True, "id": id}
