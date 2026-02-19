"""
Endpoints de Reglas por Comercio (ReglaComercio) desde Azure SQL.
Matching CONTAINS sobre razón social. Reemplaza Google Sheets.
"""
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.core.security import require_user
from app.db.catalog import _get_id_usuario
from app.db.regla_comercio import (
    list_reglas_comercio,
    create_regla_user,
    update_regla,
    delete_regla,
    get_regla_by_id,
    resolve_regla,
)
from app.storage.store import get_all

router = APIRouter()

# Prefijo de comercios virtuales (derivados de reglas)
VIRTUAL_MERCHANT_PREFIX = "comercio-"


def _merchant_id_to_patron(merchant_id: str) -> Optional[str]:
    """Resuelve merchantId a patron (nombre para matching)."""
    if not merchant_id or not isinstance(merchant_id, str):
        return None
    merchant_id = merchant_id.strip()
    if merchant_id.startswith(VIRTUAL_MERCHANT_PREFIX):
        suffix = merchant_id[len(VIRTUAL_MERCHANT_PREFIX) :]
        return suffix.replace("_", " ")
    merchants = get_all("merchants")
    for m in merchants:
        if str(m.get("id", "")).strip() == merchant_id:
            return str(m.get("name", "")).strip()
    return None


class ReglaComercioIn(BaseModel):
    """Payload nuevo: patron + idSubcategoria."""
    patron: str
    ejemploRazonSocial: Optional[str] = None
    idSubcategoria: str
    prioridad: Optional[int] = 100
    activa: Optional[bool] = True


class ReglaComercioPatch(BaseModel):
    """Patch para actualizar regla."""
    patron: Optional[str] = None
    idSubcategoria: Optional[str] = None
    prioridad: Optional[int] = None
    activa: Optional[bool] = None


class MerchantRuleIn(BaseModel):
    """Payload legacy (compatibilidad frontend)."""
    merchantId: str
    categoryId: str
    subcategoryId: Optional[str] = None


class MerchantRulePatch(BaseModel):
    """Patch legacy."""
    merchantId: Optional[str] = None
    categoryId: Optional[str] = None
    subcategoryId: Optional[str] = None


class ResolveIn(BaseModel):
    """Body para POST /reglas/resolve (debug)."""
    razonSocial: str


def _regla_to_regla_raw(r: dict) -> dict:
    """Formato ReglaRaw para frontend."""
    return {
        "id": r["id"],
        "comercio": r.get("comercio", r.get("patron", "")),
        "categoria_id": r["categoria_id"],
        "categoria_nombre": r["categoria_nombre"],
        "subcategoria_id": r["subcategoria_id"],
        "subcategoria_nombre": r["subcategoria_nombre"],
        "timestamp": r.get("timestamp") or r.get("actualizadoEn"),
    }


@router.get("")
def get_reglas(
    comercio: Optional[str] = Query(default=None),
    categoria_id: Optional[str] = Query(default=None),
    subcategoria_id: Optional[str] = Query(default=None),
    user: dict = Depends(require_user),
):
    """Lista reglas del usuario desde SQL (ReglaComercio)."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    rows = list_reglas_comercio(id_usuario)

    if comercio:
        c = comercio.strip().lower()
        rows = [r for r in rows if c in (r.get("comercio") or "").lower()]
    if categoria_id:
        cid = str(categoria_id).strip()
        rows = [r for r in rows if str(r.get("categoria_id", "")).strip() == cid]
    if subcategoria_id:
        sid = str(subcategoria_id).strip()
        rows = [r for r in rows if str(r.get("subcategoria_id", "")).strip() == sid]

    return [_regla_to_regla_raw(r) for r in rows]


@router.post("")
def post_regla(payload: dict = Body(...), user: dict = Depends(require_user)):
    """
    Crea regla. Acepta:
    - Nuevo: { patron, ejemploRazonSocial?, idSubcategoria, prioridad?, activa? }
    - Legacy: { merchantId, categoryId, subcategoryId }
    """
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Nuevo formato: patron + idSubcategoria
    if "patron" in payload and "idSubcategoria" in payload:
        patron = str(payload.get("patron") or "").strip()
        id_sub = str(payload.get("idSubcategoria") or "").strip()
        if not patron:
            raise HTTPException(status_code=400, detail="patron es requerido")
        if not id_sub:
            raise HTTPException(status_code=400, detail="idSubcategoria es requerido")
        try:
            created = create_regla_user(
                id_usuario=id_usuario,
                patron=patron,
                id_subcategoria=id_sub,
                ejemplo_razon_social=payload.get("ejemploRazonSocial"),
                prioridad=payload.get("prioridad", 100),
                activa=payload.get("activa", True),
            )
            return _regla_to_regla_raw(created)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Legacy: merchantId + categoryId + subcategoryId
    if "merchantId" in payload:
        patron = _merchant_id_to_patron(str(payload.get("merchantId", "")))
        if not patron:
            raise HTTPException(status_code=404, detail="Comercio no encontrado")
        sub_id = str(payload.get("subcategoryId") or payload.get("categoryId") or "").strip()
        if not sub_id:
            raise HTTPException(status_code=400, detail="subcategoryId o categoryId requerido")
        try:
            created = create_regla_user(
                id_usuario=id_usuario,
                patron=patron,
                id_subcategoria=sub_id,
                prioridad=100,
                activa=True,
            )
            return {
                "id": created["id"],
                "merchantId": payload.get("merchantId"),
                "categoryId": created["categoria_id"],
                "subcategoryId": created["subcategoria_id"] or None,
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    raise HTTPException(status_code=400, detail="Body inválido: use patron+idSubcategoria o merchantId+categoryId+subcategoryId")


@router.post("/resolve")
def post_resolve(payload: ResolveIn, user: dict = Depends(require_user)):
    """
    (Debug) Resuelve categoría/subcategoría para una razón social.
    No crea regla; solo diagnostica.
    """
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    result = resolve_regla(
        id_usuario=id_usuario,
        razon_social=payload.razonSocial or "",
        create_auto_if_no_match=False,
    )
    return result


@router.patch("/{id}")
def patch_regla(id: str, payload: dict, background_tasks: BackgroundTasks, user: dict = Depends(require_user)):
    """
    Actualiza regla. Acepta: patron?, idSubcategoria?, prioridad?, activa?
    O legacy: merchantId?, categoryId?, subcategoryId?
    """
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

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

    try:
        updated = update_regla(
            id_usuario=id_usuario,
            regla_id=id,
            patron=patch_patron,
            id_subcategoria=patch_sub,
            prioridad=patch_prioridad,
            activa=patch_activa,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Regla no encontrada")

        recategorization_job_id = None
        if patch_sub is not None or payload.get("categoryId") is not None or payload.get("idSubcategoria") is not None:
            from app.services.recategorizacion import enqueue_recategorization_job, process_job
            job = enqueue_recategorization_job(id_usuario, int(updated["id"]), days_back=30)
            recategorization_job_id = job["id"]
            background_tasks.add_task(process_job, id_usuario, job["id"])

        result = _regla_to_regla_raw(updated)
        if recategorization_job_id is not None:
            result["recategorization_job_id"] = recategorization_job_id
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}")
def delete_regla_endpoint(id: str, user: dict = Depends(require_user)):
    """Elimina regla."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not delete_regla(id_usuario, id):
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return {"deleted": True, "id": id}
