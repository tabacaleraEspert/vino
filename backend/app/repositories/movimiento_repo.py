"""
Async repository for Movimientos.
Uses JOINs to resolve categoría/subcategoría in a single query (no N+1).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import Select, and_, case, func, or_, select, text

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movimiento_orm import Movimiento
from app.models.categoria import Categoria
from app.models.subcategoria import SubCategoria
from app.models.regla_comercio import ReglaComercio


def _build_list_query(
    id_usuario: int,
    from_date: date | None = None,
    to_date: date | None = None,
    tipo: str | None = None,
    categoria_id: int | None = None,
    subcategoria_id: int | None = None,
    medio_carga: str | None = None,
    moneda: str | None = None,
    comercio: str | None = None,
    q: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
) -> list:
    """Build WHERE conditions list."""
    conditions = [Movimiento.Id_usuario == id_usuario]

    if from_date:
        conditions.append(Movimiento.Fecha >= from_date)
    if to_date:
        conditions.append(Movimiento.Fecha <= to_date)
    if tipo:
        conditions.append(Movimiento.TipoMovimiento == tipo.strip())
    if categoria_id is not None:
        conditions.append(Movimiento.Id_Categoria == categoria_id)
    if subcategoria_id is not None:
        conditions.append(Movimiento.Id_SubCategoria == subcategoria_id)
    if medio_carga:
        conditions.append(Movimiento.MedioCarga == medio_carga.strip())
    if moneda:
        moneda_norm = moneda.strip().upper()
        if moneda_norm == "ARS":
            conditions.append(
                or_(
                    Movimiento.Moneda == moneda_norm,
                    func.ltrim(func.rtrim(func.coalesce(Movimiento.Moneda, ""))) == "",
                )
            )
        else:
            conditions.append(Movimiento.Moneda == moneda_norm)
    if min_amount is not None:
        conditions.append(Movimiento.Monto >= min_amount)
    if max_amount is not None:
        conditions.append(Movimiento.Monto <= max_amount)
    if comercio:
        conditions.append(Movimiento.Descripcion.ilike(f"%{comercio.strip()}%"))
    if q:
        conditions.append(Movimiento.Descripcion.ilike(f"%{q.strip()}%"))

    return conditions


async def list_movimientos(
    session: AsyncSession,
    id_usuario: int,
    from_date: date | None = None,
    to_date: date | None = None,
    tipo: str | None = None,
    categoria_id: int | None = None,
    subcategoria_id: int | None = None,
    medio_carga: str | None = None,
    moneda: str | None = None,
    comercio: str | None = None,
    q: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """
    List movimientos with JOINs for categoría/subcategoría names.
    Returns (items, total_count) in a single query using window function.
    """
    conditions = _build_list_query(
        id_usuario, from_date, to_date, tipo, categoria_id, subcategoria_id,
        medio_carga, moneda, comercio, q, min_amount, max_amount,
    )

    # Count query
    count_stmt = select(func.count()).select_from(Movimiento).where(and_(*conditions))
    total = (await session.execute(count_stmt)).scalar_one()

    if total == 0:
        return [], 0

    # Main query with JOINs
    stmt = (
        select(
            Movimiento,
            Categoria.Nombre.label("categoria_nombre"),
            Categoria.Icon.label("categoria_icon"),
            Categoria.Color.label("categoria_color"),
            SubCategoria.Nombre_SubCategoria.label("subcategoria_nombre"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == Movimiento.Id_Categoria,
            Categoria.Id_usuario == Movimiento.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == Movimiento.Id_SubCategoria,
            SubCategoria.Id_usuario == Movimiento.Id_usuario,
        ))
        .where(and_(*conditions))
        .order_by(Movimiento.Fecha.desc(), Movimiento.Id.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        mov = row[0]
        items.append(_mov_to_dict(
            mov,
            categoria_nombre=row.categoria_nombre or "",
            subcategoria_nombre=row.subcategoria_nombre or "",
        ))

    return items, total


async def get_movimiento(
    session: AsyncSession,
    id_usuario: int,
    mov_id: int,
) -> dict[str, Any] | None:
    """Get single movimiento with JOINed names."""
    stmt = (
        select(
            Movimiento,
            Categoria.Nombre.label("categoria_nombre"),
            Categoria.Icon.label("categoria_icon"),
            Categoria.Color.label("categoria_color"),
            SubCategoria.Nombre_SubCategoria.label("subcategoria_nombre"),
        )
        .outerjoin(Categoria, and_(
            Categoria.Id == Movimiento.Id_Categoria,
            Categoria.Id_usuario == Movimiento.Id_usuario,
        ))
        .outerjoin(SubCategoria, and_(
            SubCategoria.Id == Movimiento.Id_SubCategoria,
            SubCategoria.Id_usuario == Movimiento.Id_usuario,
        ))
        .where(and_(
            Movimiento.Id_usuario == id_usuario,
            Movimiento.Id == mov_id,
        ))
    )

    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None

    mov = row[0]
    return _mov_to_dict(
        mov,
        categoria_nombre=row.categoria_nombre or "",
        subcategoria_nombre=row.subcategoria_nombre or "",
    )


async def create_movimiento(
    session: AsyncSession,
    id_usuario: int,
    fecha: date,
    tipo: str,
    moneda: str,
    monto: Decimal,
    medio_carga: str = "Manual",
    descripcion: str | None = None,
    id_categoria: int | None = None,
    id_subcategoria: int | None = None,
    comercio_id: str | None = None,
    categoria_manual: bool = False,
    origen: str | None = None,
    origen_id: str | None = None,
    id_credito_debito: int | None = None,
    id_medio_pago_final: int | None = None,
    cuota_actual: int | None = None,
    cuota_total: int | None = None,
    monto_total_compra: Decimal | None = None,
    id_billetera: int | None = None,
) -> dict[str, Any]:
    """Create a new movimiento and return it with JOINed names."""
    mov = Movimiento(
        Id_usuario=id_usuario,
        Fecha=fecha,
        MedioCarga=medio_carga,
        TipoMovimiento=tipo,
        Moneda=moneda,
        Monto=monto,
        Descripcion=descripcion,
        Id_Categoria=id_categoria,
        Id_SubCategoria=id_subcategoria,
        ComercioId=comercio_id,
        CategoriaManual=categoria_manual,
        Origen=origen,
        Origen_Id=origen_id,
        Id_Credito_Debito=id_credito_debito,
        Id_Medio_Pago_Final=id_medio_pago_final,
        CuotaActual=cuota_actual,
        CuotaTotal=cuota_total,
        Id_Billetera=id_billetera,
        MontoTotalCompra=monto_total_compra,
    )
    session.add(mov)
    await session.flush()
    # Re-fetch with JOINs
    return await get_movimiento(session, id_usuario, mov.Id)


async def update_movimiento(
    session: AsyncSession,
    id_usuario: int,
    mov_id: int,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Update movimiento fields. Returns updated dict or None if not found."""
    stmt = select(Movimiento).where(and_(
        Movimiento.Id_usuario == id_usuario,
        Movimiento.Id == mov_id,
    ))
    result = await session.execute(stmt)
    mov = result.scalar_one_or_none()
    if not mov:
        return None

    for key, value in updates.items():
        if hasattr(mov, key) and value is not None:
            setattr(mov, key, value)

    await session.flush()
    return await get_movimiento(session, id_usuario, mov_id)


async def delete_movimiento(
    session: AsyncSession,
    id_usuario: int,
    mov_id: int,
) -> bool:
    """Delete movimiento. Returns True if deleted."""
    stmt = select(Movimiento).where(and_(
        Movimiento.Id_usuario == id_usuario,
        Movimiento.Id == mov_id,
    ))
    result = await session.execute(stmt)
    mov = result.scalar_one_or_none()
    if not mov:
        return False
    await session.delete(mov)
    await session.flush()
    return True


async def get_movimiento_by_origen(
    session: AsyncSession,
    id_usuario: int,
    origen: str,
    origen_id: str,
) -> dict[str, Any] | None:
    """Find movimiento by Origen + Origen_Id (deduplication)."""
    stmt = select(Movimiento.Id).where(and_(
        Movimiento.Id_usuario == id_usuario,
        Movimiento.Origen == origen,
        Movimiento.Origen_Id == origen_id,
    ))
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    return await get_movimiento(session, id_usuario, row)


async def find_duplicate_cross_source(
    session: AsyncSession,
    id_usuario: int,
    monto: float,
    fecha: date,
    moneda: str = "ARS",
    descripcion: str | None = None,
    window_minutes: int = 10,
) -> dict[str, Any] | None:
    """
    Cross-source deduplication: find an existing movement with the same
    user + amount + currency + date, created within the last N minutes.

    Catches: bank email + MercadoPago email for the same purchase,
    or duplicate notifications from the same source.
    """
    from datetime import datetime, timedelta, UTC

    now = datetime.now(UTC)
    window_start = now - timedelta(minutes=window_minutes)

    # Match by: same user, same amount (exact), same currency, same date, recent timestamp
    conditions = [
        Movimiento.Id_usuario == id_usuario,
        Movimiento.Monto == monto,
        Movimiento.Moneda == moneda,
        Movimiento.Fecha == fecha,
        Movimiento.Timestamp >= window_start,
    ]

    stmt = select(Movimiento.Id).where(and_(*conditions)).order_by(Movimiento.Id.desc()).limit(1)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if not row:
        return None
    return await get_movimiento(session, id_usuario, row)


async def list_comercios_from_movimientos(
    session: AsyncSession,
    id_usuario: int,
    limit: int = 500,
) -> list[str]:
    """List unique merchant names from card/email movimientos only (not manual/whatsapp)."""
    stmt = text(
        "SELECT DISTINCT LTRIM(RTRIM(m.Descripcion)) AS nombre "
        "FROM dbo.movimientos m "
        "WHERE m.Id_usuario = :uid AND m.Descripcion IS NOT NULL "
        "AND LTRIM(RTRIM(m.Descripcion)) != '' "
        "AND m.MedioCarga IN ('Gmail', 'Statement', 'statement') "
        "ORDER BY nombre "
        "OFFSET 0 ROWS FETCH NEXT :lim ROWS ONLY"
    )
    result = await session.execute(stmt, {"uid": id_usuario, "lim": limit})
    return [str(row[0]).strip() for row in result.all() if row[0]]


def _mov_to_dict(
    mov: Movimiento,
    categoria_nombre: str = "",
    subcategoria_nombre: str = "",
) -> dict[str, Any]:
    """Convert ORM Movimiento to API dict."""
    fecha_str = mov.Fecha.strftime("%Y-%m-%d") if mov.Fecha else ""
    ts_str = mov.Timestamp.isoformat() if mov.Timestamp else ""
    tipo = "Ingreso" if str(mov.TipoMovimiento).lower() == "ingreso" else "Gasto"
    monto = round(float(mov.Monto), 2) if mov.Monto is not None else 0.0
    descripcion = str(mov.Descripcion or "").strip()

    return {
        "id": str(mov.Id),
        "Id": mov.Id,
        "fecha": fecha_str,
        "Fecha": fecha_str,
        "timestamp": ts_str,
        "Timestamp": ts_str,
        "tipo": tipo,
        "moneda": str(mov.Moneda or "").strip(),
        "Moneda": str(mov.Moneda or "").strip(),
        "monto": monto,
        "Monto": monto,
        "comercio": descripcion,
        "Comercio": descripcion,
        "comercioId": mov.ComercioId,
        "descripcion": descripcion,
        "Descripcion": descripcion,
        "categoria": categoria_nombre,
        "Nombre_Categoria": categoria_nombre,
        "subcategoria": subcategoria_nombre,
        "Nombre_SubCategoria": subcategoria_nombre,
        "idCategoria": str(mov.Id_Categoria) if mov.Id_Categoria else None,
        "idSubcategoria": str(mov.Id_SubCategoria) if mov.Id_SubCategoria else None,
        "Id_Categoria": mov.Id_Categoria,
        "Id_SubCategoria": mov.Id_SubCategoria,
        "MedioCarga": str(mov.MedioCarga or "").strip(),
        "medio_carga": str(mov.MedioCarga or "").strip(),
        "Id_Credito_Debito": mov.Id_Credito_Debito,
        "Id_Medio_Pago_Final": mov.Id_Medio_Pago_Final,
        "Origen": mov.Origen,
        "Origen_Id": mov.Origen_Id,
        "CuotaActual": mov.CuotaActual,
        "CuotaTotal": mov.CuotaTotal,
        "MontoTotalCompra": round(float(mov.MontoTotalCompra), 2) if mov.MontoTotalCompra is not None else None,
    }
