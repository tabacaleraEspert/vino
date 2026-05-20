from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Categoria(Base):
    __tablename__ = "Categoria"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("MaestroUsuarios.id"), nullable=False)
    Nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    Icon: Mapped[str | None] = mapped_column(String(50), server_default="📁")
    Color: Mapped[str | None] = mapped_column(String(20), server_default="#6b7280")
    Bucket: Mapped[str | None] = mapped_column(String(20))  # necesidades, estilo_vida, futuro
    Tipo: Mapped[str] = mapped_column(String(20), nullable=False, server_default="Gasto")  # Gasto | Ingreso
    Timestamp: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    usuario = relationship("User", back_populates="categorias")
    subcategorias = relationship("SubCategoria", back_populates="categoria", lazy="selectin")

    __table_args__ = (
        Index("IX_cat_user", "Id_usuario"),
    )
