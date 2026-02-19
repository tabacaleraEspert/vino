from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.core.security import require_user
from app.db.catalog import (
    _get_id_usuario,
    list_subcategorias_sql,
    patch_subcategoria_sql,
    delete_subcategoria_sql,
)

router = APIRouter()


class SubcategoriaPatch(BaseModel):
    name: str


def _to_frontend_subcategoria(row: dict) -> dict:
    """Formato compatible con frontend: { id, categoria_id, nombre }."""
    return {
        "id": row["id"],
        "categoria_id": row["categoria_id"],
        "nombre": row["nombre"],
    }


@router.get("")
def get_subcategorias(
    categoria_id: Optional[str] = Query(default=None),
    user: dict = Depends(require_user),
):
    """Lista subcategorías del usuario desde Azure SQL. Opcional: filtrar por categoria_id."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    cat_id = int(categoria_id) if categoria_id else None
    rows = list_subcategorias_sql(id_usuario, categoria_id=cat_id)
    return [_to_frontend_subcategoria(r) for r in rows]


@router.patch("/{id}")
def patch_subcategoria(id: str, payload: SubcategoriaPatch, user: dict = Depends(require_user)):
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    nombre = (payload.name or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    updated = patch_subcategoria_sql(id_usuario, id, nombre)
    if not updated:
        raise HTTPException(status_code=404, detail="Subcategoría no encontrada")
    return {
        "id": updated["id"],
        "name": updated["nombre"],
        "categoryId": updated["categoria_id"],
    }


@router.delete("/{id}")
def delete_subcategoria(id: str, user: dict = Depends(require_user)):
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    if not delete_subcategoria_sql(id_usuario, id):
        raise HTTPException(status_code=404, detail="Subcategoría no encontrada")
    return {"deleted": True, "id": id}
