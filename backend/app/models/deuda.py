"""Model for tracking who owes who after a split payment."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Deuda(Base):
    __tablename__ = "Deudas"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("MaestroUsuarios.id"), nullable=False)
    Id_movimiento: Mapped[int] = mapped_column(Integer, ForeignKey("movimientos.Id"), nullable=False)
    Nombre_deudor: Mapped[str] = mapped_column(String(100), nullable=False)
    Monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    Moneda: Mapped[str] = mapped_column(String(10), nullable=False, server_default="ARS")
    Pagado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    Timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    FechaPago: Mapped[datetime | None] = mapped_column(DateTime)
