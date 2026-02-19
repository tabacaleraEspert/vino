from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.security import require_user
from app.db.catalog import (
    _get_id_usuario,
    list_categorias_sql,
    create_categoria_sql,
    patch_categoria_sql,
    delete_categoria_sql,
    create_subcategoria_sql,
    get_categoria_by_id_sql,
    list_subcategorias_sql,
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


def _to_frontend_categoria(row: dict) -> dict:
    """Formato compatible con frontend (categorias list)."""
    return {"id": row["id"], "nombre": row["nombre"], "icon": row["icon"], "color": row["color"]}


@router.get("")
def get_categorias(user: dict = Depends(require_user)):
    """Lista categorías del usuario desde Azure SQL (multi-tenant)."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    rows = list_categorias_sql(id_usuario)
    return [_to_frontend_categoria(r) for r in rows]


@router.post("")
def post_categoria(payload: CategoryIn, user: dict = Depends(require_user)):
    """Crea categoría en SQL. Devuelve { id, nombre, icon, color }."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    try:
        created = create_categoria_sql(
            id_usuario=id_usuario,
            nombre=payload.name,
            icon=payload.icon,
            color=payload.color,
        )
        if payload.subcategories:
            for s in payload.subcategories:
                create_subcategoria_sql(id_usuario, created["id"], s.name)
        return _to_frontend_categoria(created)
    except KeyError:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}")
def patch_categoria(id: str, payload: CategoryPatch, user: dict = Depends(require_user)):
    """Actualiza categoría por Id. Solo campos presentes."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        cat = get_categoria_by_id_sql(id_usuario, id)
        if not cat:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return _to_frontend_categoria(cat)
    updated = patch_categoria_sql(id_usuario, id, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return _to_frontend_categoria(updated)


@router.delete("/{id}")
def delete_categoria(id: str, user: dict = Depends(require_user)):
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    if not delete_categoria_sql(id_usuario, id):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return {"deleted": True, "id": id}


@router.post("/{id}/subcategorias")
def post_subcategoria(id: str, payload: SubcategoryIn, user: dict = Depends(require_user)):
    """Crea subcategoría asociada a la categoría {id}. Valida pertenencia al usuario."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    nombre = (payload.name or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre de la subcategoría no puede estar vacío")
    try:
        created = create_subcategoria_sql(id_usuario, id, nombre)
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
