from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import set_sheets_context
from app.core.security import require_user
from app.sheets.catalog_service import (
    list_categorias as svc_list_categorias,
    create_categoria as svc_create_categoria,
    patch_categoria_by_id as svc_patch_categoria,
    delete_categoria_by_id as svc_delete_categoria,
    create_subcategoria as svc_create_subcategoria,
    get_categoria_by_id as svc_get_categoria,
)

router = APIRouter()


class SubcategoryIn(BaseModel):
    name: str  # min 1 char, no solo espacios


class CategoryIn(BaseModel):
    name: str
    icon: str = "📁"
    color: str = "#6b7280"
    subcategories: Optional[list[SubcategoryIn]] = None


class CategoryPatch(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@router.get("")
def get_categorias(user: dict = Depends(require_user)):
    set_sheets_context(user)
    return svc_list_categorias()


@router.post("")
def post_categoria(payload: CategoryIn, user: dict = Depends(require_user)):
    """Crea categoría en Sheets. Devuelve { id, nombre, icon, color }."""
    set_sheets_context(user)
    try:
        created = svc_create_categoria(
            nombre=payload.name,
            icon=payload.icon,
            color=payload.color,
        )
        if payload.subcategories:
            for s in payload.subcategories:
                svc_create_subcategoria(categoria_id=created["id"], nombre=s.name)
        return created
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}")
def patch_categoria(id: str, payload: CategoryPatch, user: dict = Depends(require_user)):
    """Actualiza categoría por Id. Solo campos presentes."""
    set_sheets_context(user)
    try:
        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            cat = svc_get_categoria(id)
            if not cat:
                raise HTTPException(status_code=404, detail="Categoría no encontrada")
            return cat
        updated = svc_patch_categoria(id, patch)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}")
def delete_categoria(id: str, user: dict = Depends(require_user)):
    set_sheets_context(user)
    if not svc_delete_categoria(id):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return {"deleted": True, "id": id}


@router.post("/{id}/subcategorias")
def post_subcategoria(id: str, payload: SubcategoryIn, user: dict = Depends(require_user)):
    """
    Crea una subcategoría asociada a la categoría {id}.
    Chequeos: categoría existe, nombre no vacío, no duplicado en la misma categoría.
    """
    set_sheets_context(user)
    nombre = (payload.name or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre de la subcategoría no puede estar vacío")
    try:
        created = svc_create_subcategoria(categoria_id=id, nombre=nombre)
        return {
            "id": created["id"],
            "name": created["nombre"],
            "categoryId": created["categoria_id"],
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
