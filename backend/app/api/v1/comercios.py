"""Endpoints de Comercios (async)."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.regla_repo import list_reglas, create_regla, update_regla
from app.repositories.movimiento_repo import list_comercios_from_movimientos
from app.utils.normalize import normalize_text

router = APIRouter()

VIRTUAL_MERCHANT_PREFIX = "comercio-"


class MerchantIn(BaseModel):
    name: str
    defaultCategoryId: Optional[str] = None
    defaultSubcategoryId: Optional[str] = None


def _id_to_merchant_name(virtual_id: str) -> str:
    if not virtual_id.startswith(VIRTUAL_MERCHANT_PREFIX):
        return virtual_id
    suffix = virtual_id[len(VIRTUAL_MERCHANT_PREFIX):]
    return suffix.replace("_", " ")


@router.get("")
async def list_comercios(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List merchants derived from reglas + movimientos."""
    reglas = await list_reglas(db, id_usuario)
    movs = await list_comercios_from_movimientos(db, id_usuario)

    reglas_names = [
        str(r.get("comercio", r.get("patron", "")) or "").strip()
        for r in reglas if (r.get("comercio") or r.get("patron"))
    ]
    all_names = list(dict.fromkeys([n for n in reglas_names + movs if n]))
    return [
        {"id": f"comercio-{normalize_text(n).replace(' ', '_')}", "name": n}
        for n in all_names
    ]


@router.post("")
async def create_comercio(
    payload: MerchantIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a merchant rule."""
    if not payload.defaultSubcategoryId:
        raise HTTPException(status_code=400, detail="defaultSubcategoryId es requerido")
    try:
        created = await create_regla(
            db, id_usuario,
            patron=payload.name,
            id_subcategoria=int(payload.defaultSubcategoryId),
        )
        return {
            "id": str(created["id"]),
            "name": created.get("comercio", payload.name),
            "defaultCategoryId": str(created["categoria_id"]) if created.get("categoria_id") else None,
            "defaultSubcategoryId": str(created["subcategoria_id"]) if created.get("subcategoria_id") else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}")
async def patch_comercio(
    id: str,
    payload: dict,
    background_tasks: BackgroundTasks,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sub_id = (payload.get("defaultSubcategoryId") or "").strip()
    cat_id = (payload.get("defaultCategoryId") or "").strip()
    if not sub_id and cat_id:
        from app.repositories.categoria_repo import list_subcategorias
        subs = await list_subcategorias(db, id_usuario, categoria_id=int(cat_id))
        sub_id = str(subs[0]["id"]) if subs else ""

    if not sub_id:
        raise HTTPException(status_code=400, detail="Se requiere defaultSubcategoryId o defaultCategoryId")

    # Find matching regla by patron
    name = _id_to_merchant_name(id) if id.startswith(VIRTUAL_MERCHANT_PREFIX) else (payload.get("name") or id)
    name_norm = normalize_text(name)
    reglas = await list_reglas(db, id_usuario)
    regla_match = [
        r for r in reglas
        if normalize_text(r.get("comercio", r.get("patron", ""))) == name_norm
    ]

    if regla_match:
        updated = await update_regla(
            db, id_usuario, regla_match[0]["id"],
            id_subcategoria=int(sub_id),
        )
        if updated:
            # Trigger recategorization
            try:
                from app.services.recategorizacion import enqueue_recategorization_job, process_job
                job = enqueue_recategorization_job(id_usuario, int(updated["id"]), days_back=30)
                background_tasks.add_task(process_job, id_usuario, job["id"])
                return {
                    "id": str(updated["id"]),
                    "name": updated.get("comercio", ""),
                    "defaultCategoryId": str(updated["categoria_id"]) if updated.get("categoria_id") else None,
                    "defaultSubcategoryId": str(updated["subcategoria_id"]) if updated.get("subcategoria_id") else None,
                    "recategorization_job_id": job["id"],
                }
            except Exception:
                pass
            return {
                "id": str(updated["id"]),
                "name": updated.get("comercio", ""),
                "defaultCategoryId": str(updated["categoria_id"]) if updated.get("categoria_id") else None,
                "defaultSubcategoryId": str(updated["subcategoria_id"]) if updated.get("subcategoria_id") else None,
            }
    else:
        # Create new regla
        created = await create_regla(
            db, id_usuario, patron=name, id_subcategoria=int(sub_id),
        )
        try:
            from app.services.recategorizacion import enqueue_recategorization_job, process_job
            job = enqueue_recategorization_job(id_usuario, int(created["id"]), days_back=365)
            background_tasks.add_task(process_job, id_usuario, job["id"])
            return {
                "id": str(created["id"]),
                "name": created.get("comercio", name),
                "defaultCategoryId": str(created["categoria_id"]) if created.get("categoria_id") else None,
                "defaultSubcategoryId": str(created["subcategoria_id"]) if created.get("subcategoria_id") else None,
                "recategorization_job_id": job["id"],
            }
        except Exception:
            pass
        return {
            "id": str(created["id"]),
            "name": created.get("comercio", name),
            "defaultCategoryId": str(created["categoria_id"]) if created.get("categoria_id") else None,
            "defaultSubcategoryId": str(created["subcategoria_id"]) if created.get("subcategoria_id") else None,
        }


@router.delete("/{id}")
async def delete_comercio(
    id: str,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Find and delete matching regla
    name = _id_to_merchant_name(id) if id.startswith(VIRTUAL_MERCHANT_PREFIX) else id
    name_norm = normalize_text(name)
    reglas = await list_reglas(db, id_usuario)
    regla_match = [
        r for r in reglas
        if normalize_text(r.get("comercio", r.get("patron", ""))) == name_norm
    ]
    if not regla_match:
        raise HTTPException(status_code=404, detail="Comercio no encontrado")

    from app.repositories.regla_repo import delete_regla
    await delete_regla(db, id_usuario, regla_match[0]["id"])
    return {"deleted": True, "id": id}
