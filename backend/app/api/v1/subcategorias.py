from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.api.deps import set_sheets_context
from app.core.security import require_user
from app.sheets.catalog_service import (
    list_subcategorias,
    patch_subcategoria_by_id,
    delete_subcategoria_by_id,
)

router = APIRouter()


class SubcategoriaPatch(BaseModel):
    name: str


@router.get("")
def get_subcategorias(
    categoria_id: Optional[str] = Query(default=None),
    user: dict = Depends(require_user),
):
    set_sheets_context(user)
    return list_subcategorias(categoria_id=categoria_id)




@router.patch("/{id}")
def patch_subcategoria(id: str, payload: SubcategoriaPatch, user: dict = Depends(require_user)):
    set_sheets_context(user)
    nombre = (payload.name or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    try:
        updated = patch_subcategoria_by_id(id, nombre)
        return {
            "id": updated["id"],
            "name": updated["nombre"],
            "categoryId": updated["categoria_id"],
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Subcategoría no encontrada")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}")
def delete_subcategoria(id: str, user: dict = Depends(require_user)):
    set_sheets_context(user)
    if not delete_subcategoria_by_id(id):
        raise HTTPException(status_code=404, detail="Subcategoría no encontrada")
    return {"deleted": True, "id": id}
