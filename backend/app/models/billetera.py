"""Model for user wallets/accounts (multi-currency support)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Billetera(Base):
    __tablename__ = "Billeteras"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("MaestroUsuarios.id"), nullable=False)
    Nombre: Mapped[str] = mapped_column(String(100), nullable=False)  # "Cuenta Pesos", "Cuenta Dólares"
    Moneda: Mapped[str] = mapped_column(String(10), nullable=False)  # ARS, USD, EUR
    Icono: Mapped[str | None] = mapped_column(String(10))  # 🇦🇷, 🇺🇸
    Color: Mapped[str | None] = mapped_column(String(20))  # #hex
    SaldoInicial: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    Activa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    EsDefault: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    Timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
