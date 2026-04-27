from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Movimiento(Base):
    __tablename__ = "movimientos"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("MaestroUsuarios.id"), nullable=False)
    Fecha: Mapped[date] = mapped_column(Date, nullable=False)
    Timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    MedioCarga: Mapped[str] = mapped_column(String(30), nullable=False)
    TipoMovimiento: Mapped[str] = mapped_column(String(20), nullable=False)
    Moneda: Mapped[str] = mapped_column(String(10), nullable=False)
    Monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    Id_Credito_Debito: Mapped[int | None] = mapped_column(Integer)
    Id_Medio_Pago_Final: Mapped[int | None] = mapped_column(Integer)
    Descripcion: Mapped[str | None] = mapped_column(String(500))
    Id_Categoria: Mapped[int | None] = mapped_column(Integer, ForeignKey("Categoria.Id"))
    Id_SubCategoria: Mapped[int | None] = mapped_column(Integer, ForeignKey("SubCategoria.Id"))
    Origen: Mapped[str | None] = mapped_column(String(50))
    Origen_Id: Mapped[str | None] = mapped_column(String(120))
    ComercioId: Mapped[str | None] = mapped_column(String(120))
    CategoriaManual: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    # Cuotas
    CuotaActual: Mapped[int | None] = mapped_column(Integer)
    CuotaTotal: Mapped[int | None] = mapped_column(Integer)
    MontoTotalCompra: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

    # Split / "Pagué yo"
    EsSplit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    SplitTotal: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    SplitParticipantes: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    usuario = relationship("User", back_populates="movimientos")
    categoria = relationship("Categoria", lazy="joined")
    subcategoria = relationship("SubCategoria", lazy="joined")

    __table_args__ = (
        Index("IX_movimientos_Id_usuario", "Id_usuario"),
        Index("IX_movimientos_Fecha", "Id_usuario", "Fecha"),
        Index("IX_movimientos_Origen", "Id_usuario", "Origen", "Origen_Id"),
        Index("IX_movimientos_Tipo_Fecha", "Id_usuario", "TipoMovimiento", "Fecha", "Moneda"),
        Index("IX_movimientos_Categoria", "Id_usuario", "Id_Categoria", "Fecha"),
    )
