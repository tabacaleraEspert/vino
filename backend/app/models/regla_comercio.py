from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReglaComercio(Base):
    __tablename__ = "ReglaComercio"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("MaestroUsuarios.id"), nullable=False)
    Patron: Mapped[str] = mapped_column(String(120), nullable=False)
    PatronNorm: Mapped[str] = mapped_column(String(120), nullable=False)
    EjemploRazonSocial: Mapped[str | None] = mapped_column(String(300))
    Id_Categoria: Mapped[int] = mapped_column(Integer, ForeignKey("Categoria.Id"), nullable=False)
    Id_SubCategoria: Mapped[int] = mapped_column(Integer, ForeignKey("SubCategoria.Id"), nullable=False)
    Prioridad: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    Activa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    Confianza: Mapped[str] = mapped_column(String(20), nullable=False, server_default="AUTO")
    CreadoEn: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    ActualizadoEn: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    categoria = relationship("Categoria", lazy="joined")
    subcategoria = relationship("SubCategoria", lazy="joined")

    __table_args__ = (
        UniqueConstraint("Id_usuario", "PatronNorm", name="UQ_ReglaComercio_Usuario_PatronNorm"),
        Index("IX_ReglaComercio_Id_usuario", "Id_usuario"),
        Index("IX_ReglaComercio_Activa", "Id_usuario", "Activa"),
    )
