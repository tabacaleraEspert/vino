"""Endpoints for bank statement upload, AI extraction, and bulk transaction creation."""
import logging
from datetime import date
from decimal import Decimal
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.repositories.categoria_repo import list_categorias, list_subcategorias
from app.repositories.movimiento_repo import create_movimiento, get_movimiento_by_origen
from app.repositories.regla_repo import resolve_regla
from app.services.statement_parser import make_origen_id, parse_statement
from app.utils.parse_utils import parse_date_flex

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/extract")
async def extract_statement(
    file: UploadFile = File(...),
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a bank statement (PDF or image) and extract transactions with AI.
    Returns extracted transactions for user review before confirming.
    """
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Tipo de archivo no detectado")

    allowed_types = {
        "application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }
    allowed_ext = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xlsx", ".xls"}
    fname = (file.filename or "").lower()
    ext_ok = any(fname.endswith(e) for e in allowed_ext)
    if file.content_type not in allowed_types and not ext_ok:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {file.content_type}. Usa PDF, JPG, PNG o Excel (.xlsx).",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="El archivo supera los 10MB")

    # Load user categories + subcategories for AI context
    cats = await list_categorias(db, id_usuario)
    subs = await list_subcategorias(db, id_usuario)

    # Build categories with subcategories for the prompt
    sub_by_cat: dict[int, list] = {}
    for s in subs:
        cid = s.get("categoria_id")
        if cid:
            sub_by_cat.setdefault(cid, []).append(s)

    cats_with_subs = []
    for c in cats:
        entry = {**c, "subcategorias": sub_by_cat.get(c["id"], [])}
        cats_with_subs.append(entry)

    # Extract
    result = await parse_statement(
        file_bytes, file.filename or "file", file.content_type or "", cats_with_subs
    )

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    # Enrich transactions with category names
    cat_map = {c["id"]: c["nombre"] for c in cats}
    sub_map = {s["id"]: s["nombre"] for s in subs}

    for tx in result.get("transactions", []):
        cid = tx.get("categoria_id")
        sid = tx.get("subcategoria_id")
        tx["categoria_nombre"] = cat_map.get(cid, "") if cid else ""
        tx["subcategoria_nombre"] = sub_map.get(sid, "") if sid else ""
        tx["included"] = True

    return {
        "status": "ok",
        "statement_period": result.get("statement_period", ""),
        "card_or_account": result.get("card_or_account", ""),
        "transactions": result.get("transactions", []),
        "total": len(result.get("transactions", [])),
    }


# --- Confirm & create movements ---

class ExtractedTransaction(BaseModel):
    fecha: str
    descripcion: str
    monto: float
    moneda: str = "ARS"
    tipo: Literal["Gasto", "Ingreso"] = "Gasto"
    categoria_id: int | None = None
    subcategoria_id: int | None = None
    included: bool = True


class StatementConfirmPayload(BaseModel):
    transactions: List[ExtractedTransaction]
    origen_label: str = "Statement"


@router.post("/confirm")
async def confirm_statement(
    payload: StatementConfirmPayload,
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm extracted transactions and create movements.
    Only creates transactions marked as included=True.
    """
    included = [t for t in payload.transactions if t.included]
    if not included:
        raise HTTPException(status_code=400, detail="No hay transacciones seleccionadas")

    created = 0
    duplicated = 0
    errors = []

    for i, tx in enumerate(included):
        try:
            fecha = parse_date_flex(tx.fecha)
            if not fecha:
                errors.append({"index": i, "error": f"Fecha invalida: {tx.fecha}"})
                continue

            origen_id = make_origen_id(tx.fecha, tx.monto, tx.descripcion)

            # Dedup
            existing = await get_movimiento_by_origen(
                db, id_usuario, payload.origen_label, origen_id
            )
            if existing:
                duplicated += 1
                continue

            # Resolve category from regla if not provided
            cat_id = tx.categoria_id
            sub_id = tx.subcategoria_id
            if not cat_id and tx.descripcion:
                regla = await resolve_regla(db, id_usuario, tx.descripcion)
                if regla:
                    cat_id = regla["categoria_id"]
                    sub_id = regla["subcategoria_id"]

            await create_movimiento(
                db,
                id_usuario=id_usuario,
                fecha=fecha,
                tipo=tx.tipo,
                moneda=tx.moneda,
                monto=Decimal(str(round(tx.monto, 2))),
                medio_carga="Statement",
                descripcion=tx.descripcion,
                id_categoria=cat_id,
                id_subcategoria=sub_id,
                comercio_id=None,
                categoria_manual=bool(tx.categoria_id),
                origen=payload.origen_label,
                origen_id=origen_id,
                id_credito_debito=None,
                id_medio_pago_final=None,
            )
            created += 1

        except Exception as e:
            logger.warning("Error creating tx %d: %s", i, e)
            errors.append({"index": i, "error": str(e)})

    return {
        "status": "ok",
        "total": len(included),
        "creados": created,
        "duplicados": duplicated,
        "errores": len(errors),
        "detalle_errores": errors[:10],
    }
