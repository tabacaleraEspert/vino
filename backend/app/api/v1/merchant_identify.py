"""Endpoints for merchant identification and uncategorized transaction management."""
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.categoria_repo import list_categorias, list_subcategorias
from app.repositories.movimiento_repo import list_movimientos
from app.repositories.regla_repo import resolve_regla, create_regla
from app.services.merchant_identifier import identify_and_suggest_category, identify_merchants_batch
from app.utils.parse_utils import parse_period

logger = logging.getLogger(__name__)
router = APIRouter()

# Default category/subcategory IDs for uncategorized
DEFAULT_CAT_ID = 6
DEFAULT_SUBCAT_ID = 42


@router.post("/identify")
async def identify_merchant_endpoint(
    payload: dict,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Identify an unknown merchant name and suggest a category.
    Uses AI + optional web search.
    """
    merchant_name = (payload.get("merchant_name") or "").strip()
    if not merchant_name:
        raise HTTPException(status_code=400, detail="merchant_name es requerido")

    cats = await list_categorias(db, id_usuario)
    subs = await list_subcategorias(db, id_usuario)
    sub_by_cat: dict[int, list] = {}
    for s in subs:
        cid = s.get("categoria_id")
        if cid:
            sub_by_cat.setdefault(cid, []).append(s)
    cats_with_subs = [{**c, "subcategorias": sub_by_cat.get(c["id"], [])} for c in cats]

    result = await identify_and_suggest_category(merchant_name, cats_with_subs)
    return result


class IdentifyBatchRequest(BaseModel):
    merchant_names: List[str]


@router.post("/identify/batch")
async def identify_merchants_batch_endpoint(
    payload: IdentifyBatchRequest,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Identify multiple merchants in a single AI call.
    Much faster than calling /identify for each one.
    """
    if not payload.merchant_names:
        raise HTTPException(status_code=400, detail="merchant_names es requerido")
    if len(payload.merchant_names) > 50:
        raise HTTPException(status_code=400, detail="Maximo 50 comercios por batch")

    cats = await list_categorias(db, id_usuario)
    subs = await list_subcategorias(db, id_usuario)
    sub_by_cat: dict[int, list] = {}
    for s in subs:
        cid = s.get("categoria_id")
        if cid:
            sub_by_cat.setdefault(cid, []).append(s)
    cats_with_subs = [{**c, "subcategorias": sub_by_cat.get(c["id"], [])} for c in cats]

    results = await identify_merchants_batch(payload.merchant_names, cats_with_subs)
    return {"results": results}


@router.get("/uncategorized")
async def list_uncategorized(
    period: Optional[str] = Query(default=None, description="YYYY-MM"),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    List transactions in the default 'Otros/Gastos no categorizados' category.
    These are the ones that need review.
    """
    from_date = None
    to_date = None
    if period:
        try:
            from_date, to_date = parse_period(period)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    items, total = await list_movimientos(
        db, id_usuario,
        from_date=from_date, to_date=to_date,
        categoria_id=DEFAULT_CAT_ID,
        limit=100, offset=0,
    )

    # Group by unique merchant name
    by_merchant: dict[str, dict] = {}
    for item in items:
        comercio = (
            item.get("comercio") or item.get("Comercio") or
            item.get("descripcion") or item.get("Descripcion") or ""
        ).strip()
        if not comercio:
            continue
        if comercio not in by_merchant:
            by_merchant[comercio] = {
                "comercio": comercio,
                "count": 0,
                "total_monto": 0,
                "movimiento_ids": [],
                "last_fecha": "",
            }
        by_merchant[comercio]["count"] += 1
        by_merchant[comercio]["total_monto"] += float(item.get("monto", 0))
        by_merchant[comercio]["movimiento_ids"].append(item.get("id"))
        fecha = item.get("fecha", "")
        if fecha > by_merchant[comercio]["last_fecha"]:
            by_merchant[comercio]["last_fecha"] = fecha

    # Sort by count descending
    merchants = sorted(by_merchant.values(), key=lambda x: x["count"], reverse=True)

    return {
        "total_uncategorized": total,
        "unique_merchants": len(merchants),
        "merchants": merchants,
    }


class CategorizeRequest(BaseModel):
    comercio: str
    categoria_id: int
    subcategoria_id: int | None = None
    create_rule: bool = True


class BulkCategorizeRequest(BaseModel):
    items: List[CategorizeRequest]


@router.post("/categorize")
async def categorize_merchant(
    payload: CategorizeRequest,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Categorize a merchant: update all its uncategorized transactions
    and optionally create a rule for future transactions.
    """
    from sqlalchemy import and_, select, update
    from app.models.movimiento_orm import Movimiento

    comercio = payload.comercio.strip()
    if not comercio:
        raise HTTPException(status_code=400, detail="comercio es requerido")

    # Update all uncategorized transactions with this merchant name
    stmt = (
        update(Movimiento)
        .where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.Id_Categoria == DEFAULT_CAT_ID,
            Movimiento.Descripcion.contains(comercio),
        ))
        .values(
            Id_Categoria=payload.categoria_id,
            Id_SubCategoria=payload.subcategoria_id,
        )
    )
    result = await db.execute(stmt)
    updated = result.rowcount

    # Create rule for future transactions
    rule_created = False
    if payload.create_rule:
        try:
            existing = await resolve_regla(db, id_usuario, comercio)
            if existing:
                # Update existing rule
                from app.models.regla_comercio import ReglaComercio
                regla_stmt = select(ReglaComercio).where(ReglaComercio.Id == existing["id"])
                regla_result = await db.execute(regla_stmt)
                regla = regla_result.scalar_one_or_none()
                if regla:
                    regla.Id_Categoria = payload.categoria_id
                    regla.Id_SubCategoria = payload.subcategoria_id
                    regla.Confianza = "MANUAL"
                    await db.flush()
                    rule_created = True
            else:
                await create_regla(
                    db,
                    id_usuario=id_usuario,
                    patron=comercio,
                    id_categoria=payload.categoria_id,
                    id_subcategoria=payload.subcategoria_id,
                    confianza="MANUAL",
                )
                rule_created = True
        except Exception as e:
            logger.warning("Failed to create/update rule for '%s': %s", comercio, e)

    await db.flush()

    return {
        "comercio": comercio,
        "transactions_updated": updated,
        "rule_created": rule_created,
        "categoria_id": payload.categoria_id,
    }


@router.post("/categorize/bulk")
async def bulk_categorize(
    payload: BulkCategorizeRequest,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Categorize multiple merchants at once."""
    results = []
    for item in payload.items:
        try:
            # Reuse single categorize logic inline
            from sqlalchemy import and_, update
            from app.models.movimiento_orm import Movimiento

            stmt = (
                update(Movimiento)
                .where(and_(
                    Movimiento.Id_usuario == id_usuario,
                    Movimiento.Id_Categoria == DEFAULT_CAT_ID,
                    Movimiento.Descripcion.contains(item.comercio),
                ))
                .values(
                    Id_Categoria=item.categoria_id,
                    Id_SubCategoria=item.subcategoria_id,
                )
            )
            result = await db.execute(stmt)

            if item.create_rule:
                try:
                    await create_regla(
                        db,
                        id_usuario=id_usuario,
                        patron=item.comercio,
                        id_categoria=item.categoria_id,
                        id_subcategoria=item.subcategoria_id,
                        confianza="MANUAL",
                    )
                except Exception:
                    pass

            results.append({
                "comercio": item.comercio,
                "transactions_updated": result.rowcount,
                "status": "ok",
            })
        except Exception as e:
            results.append({
                "comercio": item.comercio,
                "transactions_updated": 0,
                "status": "error",
                "error": str(e),
            })

    await db.flush()

    return {
        "total": len(payload.items),
        "categorized": sum(1 for r in results if r["status"] == "ok"),
        "results": results,
    }
