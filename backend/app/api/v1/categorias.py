from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.categoria_repo import (
    list_categorias,
    get_categoria,
    create_categoria,
    update_categoria,
    delete_categoria,
    create_subcategoria,
)

router = APIRouter()


class SubcategoryIn(BaseModel):
    name: str


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
async def get_categorias(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await list_categorias(db, id_usuario)


@router.post("")
async def post_categoria(
    payload: CategoryIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    created = await create_categoria(db, id_usuario, nombre=payload.name, icon=payload.icon, color=payload.color)
    if payload.subcategories:
        for s in payload.subcategories:
            await create_subcategoria(db, id_usuario, categoria_id=created["id"], nombre=s.name)
    return created


@router.patch("/{id}")
async def patch_categoria(
    id: int,
    payload: CategoryPatch,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        cat = await get_categoria(db, id_usuario, id)
        if not cat:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return cat
    updated = await update_categoria(db, id_usuario, id, **patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return updated


@router.delete("/{id}")
async def delete_categoria_endpoint(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not await delete_categoria(db, id_usuario, id):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return {"deleted": True, "id": str(id)}


@router.post("/{id}/subcategorias")
async def post_subcategoria(
    id: int,
    payload: SubcategoryIn,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    nombre = (payload.name or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre de la subcategoría no puede estar vacío")
    created = await create_subcategoria(db, id_usuario, categoria_id=id, nombre=nombre)
    return {"id": created["id"], "name": created["nombre"], "categoryId": created["categoria_id"]}
