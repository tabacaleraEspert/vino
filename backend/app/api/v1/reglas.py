"""Endpoints de Reglas por Comercio (async)."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.regla_repo import (
    list_reglas,
    get_regla,
    create_regla,
    update_regla,
    delete_regla,
    resolve_regla,
)

router = APIRouter()

VIRTUAL_MERCHANT_PREFIX = "comercio-"


class ReglaComercioIn(BaseModel):
    patron: str
    ejemploRazonSocial: Optional[str] = None
    idSubcategoria: str
    prioridad: Optional[int] = 100
    activa: Optional[bool] = True


class ResolveIn(BaseModel):
    razonSocial: str


def _to_raw(r: dict) -> dict:
    return {
        "id": r["id"],
        "comercio": r.get("comercio", r.get("patron", "")),
        "categoria_id": r["categoria_id"],
        "categoria_nombre": r.get("categoria_nombre", ""),
        "subcategoria_id": r["subcategoria_id"],
        "subcategoria_nombre": r.get("subcategoria_nombre", ""),
        "timestamp": r.get("timestamp", ""),
    }


def _merchant_id_to_patron(merchant_id: str) -> Optional[str]:
    if not merchant_id:
        return None
    merchant_id = merchant_id.strip()
    if merchant_id.startswith(VIRTUAL_MERCHANT_PREFIX):
        suffix = merchant_id[len(VIRTUAL_MERCHANT_PREFIX):]
        return suffix.replace("_", " ")
    return None


@router.get("")
async def get_reglas(
    comercio: Optional[str] = Query(default=None),
    categoria_id: Optional[str] = Query(default=None),
    subcategoria_id: Optional[str] = Query(default=None),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_reglas(db, id_usuario)

    if comercio:
        c = comercio.strip().lower()
        rows = [r for r in rows if c in (r.get("comercio") or "").lower()]
    if categoria_id:
        cid = str(categoria_id).strip()
        rows = [r for r in rows if str(r.get("categoria_id", "")).strip() == cid]
    if subcategoria_id:
        sid = str(subcategoria_id).strip()
        rows = [r for r in rows if str(r.get("subcategoria_id", "")).strip() == sid]

    return [_to_raw(r) for r in rows]


@router.post("")
async def post_regla(
    payload: dict = Body(...),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Crea regla. Acepta:
    - Nuevo: { patron, idSubcategoria, prioridad?, activa? }
    - Legacy: { merchantId, categoryId, subcategoryId }
    """
    # Nuevo formato
    if "patron" in payload and "idSubcategoria" in payload:
        patron = str(payload.get("patron") or "").strip()
        id_sub = str(payload.get("idSubcategoria") or "").strip()
        if not patron:
            raise HTTPException(status_code=400, detail="patron es requerido")
        if not id_sub:
            raise HTTPException(status_code=400, detail="idSubcategoria es requerido")
        try:
            created = await create_regla(
                db, id_usuario,
                patron=patron,
                id_subcategoria=int(id_sub),
                prioridad=payload.get("prioridad", 100),
                confianza="MANUAL",
            )
            return _to_raw(created)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Legacy: merchantId
    if "merchantId" in payload:
        patron = _merchant_id_to_patron(str(payload.get("merchantId", "")))
        if not patron:
            raise HTTPException(status_code=404, detail="Comercio no encontrado")
        sub_id = str(payload.get("subcategoryId") or "").strip()
        cat_id = str(payload.get("categoryId") or "").strip()
        if not sub_id and not cat_id:
            raise HTTPException(status_code=400, detail="subcategoryId o categoryId requerido")
        try:
            created = await create_regla(
                db, id_usuario, patron=patron,
                id_subcategoria=int(sub_id) if sub_id else None,
                id_categoria=int(cat_id) if cat_id and not sub_id else None,
            )
            return {
                "id": created["id"],
                "merchantId": payload.get("merchantId"),
                "categoryId": created["categoria_id"],
                "subcategoryId": created["subcategoria_id"] or None,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    raise HTTPException(status_code=400, detail="Body inválido")


@router.post("/resolve")
async def post_resolve(
    payload: ResolveIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await resolve_regla(db, id_usuario, payload.razonSocial or "")
    return result or {"match": False}


@router.patch("/{id}")
async def patch_regla(
    id: int,
    payload: dict,
    background_tasks: BackgroundTasks,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    patch_patron = payload.get("patron")
    patch_sub = payload.get("idSubcategoria") or payload.get("subcategoryId")
    patch_prioridad = payload.get("prioridad")
    patch_activa = payload.get("activa")

    if "merchantId" in payload:
        patron = _merchant_id_to_patron(payload["merchantId"])
        if patron:
            patch_patron = patron
    if "categoryId" in payload and not patch_sub:
        patch_sub = payload.get("subcategoryId") or payload.get("categoryId")

    updated = await update_regla(
        db, id_usuario, id,
        patron=patch_patron,
        id_subcategoria=int(patch_sub) if patch_sub else None,
        prioridad=patch_prioridad,
        activa=patch_activa,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    # Trigger recategorization in background (still uses old sync service)
    recategorization_job_id = None
    if patch_sub is not None:
        try:
            from app.services.recategorizacion import enqueue_recategorization_job, process_job
            job = enqueue_recategorization_job(id_usuario, int(updated["id"]), days_back=30)
            recategorization_job_id = job["id"]
            background_tasks.add_task(process_job, id_usuario, job["id"])
        except Exception:
            pass

    result = _to_raw(updated)
    if recategorization_job_id is not None:
        result["recategorization_job_id"] = recategorization_job_id
    return result


@router.delete("/{id}")
async def delete_regla_endpoint(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not await delete_regla(db, id_usuario, id):
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return {"deleted": True, "id": str(id)}
