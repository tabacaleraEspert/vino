import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sa_delete

from app.db.session import get_db
from app.deps import get_current_user_id
from app.models.categoria import Categoria
from app.models.subcategoria import SubCategoria
from app.repositories.categoria_repo import (
    list_categorias,
    get_categoria,
    create_categoria,
    update_categoria,
    delete_categoria,
    create_subcategoria,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class SubcategoryIn(BaseModel):
    name: str


class CategoryIn(BaseModel):
    name: str
    icon: str = "📁"
    color: str = "#6b7280"
    subcategories: Optional[list[SubcategoryIn]] = None


class OnboardingCatIn(BaseModel):
    nombre: str
    icon: str = "📁"
    color: str = "#6b7280"
    bucket: str = "necesidades"
    subcategorias: list[str] = []


class OnboardingPayload(BaseModel):
    categorias: list[OnboardingCatIn]


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


@router.post("/onboarding")
async def onboarding_categories(
    payload: OnboardingPayload,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Replace all categories for this user with the onboarding selection."""
    # Delete existing subcategories and categories
    await db.execute(sa_delete(SubCategoria).where(SubCategoria.Id_usuario == id_usuario))
    await db.execute(sa_delete(Categoria).where(Categoria.Id_usuario == id_usuario))
    await db.flush()

    created = 0
    for cat_data in payload.categorias:
        cat = Categoria(
            Id_usuario=id_usuario,
            Nombre=cat_data.nombre,
            Icon=cat_data.icon,
            Color=cat_data.color,
            Bucket=cat_data.bucket,
        )
        db.add(cat)
        await db.flush()

        for sub_name in cat_data.subcategorias:
            sub = SubCategoria(
                Id_usuario=id_usuario,
                Id_Categoria=cat.Id,
                Nombre_SubCategoria=sub_name,
            )
            db.add(sub)
            created += 1
        created += 1

    await db.flush()
    logger.info("Onboarding categories: %d items for user %d", created, id_usuario)
    return {"created": created}


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
