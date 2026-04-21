from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Presupuesto(Base):
    __tablename__ = "Presupuestos"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("MaestroUsuarios.id"), nullable=False)
    PeriodoMes: Mapped[date] = mapped_column(Date, nullable=False)
    Id_Categoria: Mapped[int | None] = mapped_column(Integer, ForeignKey("Categoria.Id"))
    Id_SubCategoria: Mapped[int | None] = mapped_column(Integer, ForeignKey("SubCategoria.Id"))
    Monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    Timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    categoria = relationship("Categoria", lazy="joined")
    subcategoria = relationship("SubCategoria", lazy="joined")

    __table_args__ = (
        Index("IX_Presupuestos_Id_usuario", "Id_usuario"),
        Index("IX_Presupuestos_Id_usuario_PeriodoMes", "Id_usuario", "PeriodoMes"),
    )
