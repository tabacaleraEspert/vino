from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.categoria_repo import (
    list_subcategorias,
    update_subcategoria,
    delete_subcategoria,
)

router = APIRouter()


class SubcategoriaPatch(BaseModel):
    name: str


@router.get("")
async def get_subcategorias(
    categoria_id: Optional[str] = Query(default=None),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    cat_id = int(categoria_id) if categoria_id else None
    return await list_subcategorias(db, id_usuario, categoria_id=cat_id)


@router.patch("/{id}")
async def patch_subcategoria(
    id: int,
    payload: SubcategoriaPatch,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    nombre = (payload.name or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    updated = await update_subcategoria(db, id_usuario, id, nombre=nombre)
    if not updated:
        raise HTTPException(status_code=404, detail="Subcategoría no encontrada")
    return {"id": updated["id"], "name": updated["nombre"], "categoryId": updated["categoria_id"]}


@router.delete("/{id}")
async def delete_subcategoria_endpoint(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not await delete_subcategoria(db, id_usuario, id):
        raise HTTPException(status_code=404, detail="Subcategoría no encontrada")
    return {"deleted": True, "id": str(id)}
