"""Admin dashboard: stats, ingestas recientes, reglas AUTO."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_user_id
from app.models.movimiento_orm import Movimiento
from app.models.regla_comercio import ReglaComercio
from app.models.categoria import Categoria
from app.models.subcategoria import SubCategoria
from app.models.user import User

router = APIRouter()


@router.get("/dashboard")
async def admin_dashboard(
    id_usuario: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Panel de monitoreo: stats del sistema, ingestas recientes, reglas AUTO."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    # --- Counts (en paralelo con asyncio no aplica, pero son queries livianas) ---

    # Total usuarios
    total_usuarios = (await db.execute(select(func.count()).select_from(User))).scalar() or 0

    # Movimientos: total, hoy, semana
    base = select(func.count()).where(Movimiento.Id_usuario == id_usuario)
    mov_total = (await db.execute(base)).scalar() or 0
    mov_hoy = (await db.execute(base.where(Movimiento.Fecha == today))).scalar() or 0
    mov_semana = (await db.execute(base.where(Movimiento.Fecha >= week_ago))).scalar() or 0

    # Reglas: total, AUTO
    regla_base = select(func.count()).where(ReglaComercio.Id_usuario == id_usuario)
    reglas_total = (await db.execute(regla_base)).scalar() or 0
    reglas_auto = (await db.execute(
        regla_base.where(ReglaComercio.Confianza == "AUTO")
    )).scalar() or 0

    # --- Ingestas recientes (últimos 10 movimientos de Gmail) ---
    ingest_stmt = (
        select(
            Movimiento.Id,
            Movimiento.Fecha,
            Movimiento.Timestamp,
            Movimiento.Descripcion,
            Movimiento.Monto,
            Movimiento.Moneda,
            Movimiento.Origen,
            Movimiento.ComercioId,
            Categoria.Nombre.label("categoria"),
            SubCategoria.Nombre_SubCategoria.label("subcategoria"),
            ReglaComercio.Confianza.label("regla_confianza"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == Movimiento.Id_Categoria,
            Categoria.Id_usuario == Movimiento.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == Movimiento.Id_SubCategoria,
            SubCategoria.Id_usuario == Movimiento.Id_usuario,
        ))
        .outerjoin(ReglaComercio, and_(
            ReglaComercio.Id == cast(Movimiento.ComercioId, Integer),
            ReglaComercio.Id_usuario == Movimiento.Id_usuario,
        ))
        .where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.MedioCarga == "Gmail",
        ))
        .order_by(Movimiento.Timestamp.desc())
        .limit(10)
    )
    ingest_rows = (await db.execute(ingest_stmt)).all()
    ingest_recientes = [
        {
            "id": r.Id,
            "fecha": r.Fecha.isoformat() if r.Fecha else "",
            "timestamp": r.Timestamp.isoformat() if r.Timestamp else "",
            "descripcion": r.Descripcion or "",
            "monto": float(r.Monto) if r.Monto else 0,
            "moneda": r.Moneda or "ARS",
            "categoria": r.categoria or "Sin categoría",
            "subcategoria": r.subcategoria or "",
            "regla_confianza": r.regla_confianza or "SIN_REGLA",
        }
        for r in ingest_rows
    ]

    # --- Reglas AUTO recientes (últimas 5) ---
    reglas_stmt = (
        select(
            ReglaComercio.Id,
            ReglaComercio.Patron,
            ReglaComercio.Confianza,
            ReglaComercio.CreadoEn,
            Categoria.Nombre.label("categoria"),
            SubCategoria.Nombre_SubCategoria.label("subcategoria"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == ReglaComercio.Id_Categoria,
            Categoria.Id_usuario == ReglaComercio.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == ReglaComercio.Id_SubCategoria,
            SubCategoria.Id_usuario == ReglaComercio.Id_usuario,
        ))
        .where(and_(
            ReglaComercio.Id_usuario == id_usuario,
            ReglaComercio.Confianza == "AUTO",
        ))
        .order_by(ReglaComercio.CreadoEn.desc())
        .limit(5)
    )
    reglas_rows = (await db.execute(reglas_stmt)).all()
    reglas_recientes = [
        {
            "id": r.Id,
            "patron": r.Patron,
            "categoria": r.categoria or "",
            "subcategoria": r.subcategoria or "",
            "confianza": r.Confianza,
            "creado_en": r.CreadoEn.isoformat() if r.CreadoEn else "",
        }
        for r in reglas_rows
    ]

    # --- Movimientos por día (últimos 7 días) ---
    dias_stmt = (
        select(
            Movimiento.Fecha,
            func.count().label("count"),
            func.sum(Movimiento.Monto).label("total"),
        )
        .where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.Fecha >= week_ago,
        ))
        .group_by(Movimiento.Fecha)
        .order_by(Movimiento.Fecha.asc())
    )
    dias_rows = (await db.execute(dias_stmt)).all()
    # Completar días sin movimientos
    dias_map = {r.Fecha: {"count": r.count, "total": float(r.total or 0)} for r in dias_rows}
    movimientos_por_dia = []
    for i in range(7):
        d = week_ago + timedelta(days=i)
        data = dias_map.get(d, {"count": 0, "total": 0})
        movimientos_por_dia.append({
            "fecha": d.isoformat(),
            "count": data["count"],
            "total": round(data["total"], 2),
        })

    return {
        "system": {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "counts": {
            "usuarios": total_usuarios,
            "movimientos_total": mov_total,
            "movimientos_hoy": mov_hoy,
            "movimientos_semana": mov_semana,
            "reglas_total": reglas_total,
            "reglas_auto": reglas_auto,
        },
        "ingest_recientes": ingest_recientes,
        "reglas_recientes": reglas_recientes,
        "movimientos_por_dia": movimientos_por_dia,
    }
