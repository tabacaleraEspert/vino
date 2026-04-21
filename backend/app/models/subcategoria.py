from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SubCategoria(Base):
    __tablename__ = "SubCategoria"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("MaestroUsuarios.id"), nullable=False)
    Id_Categoria: Mapped[int] = mapped_column(Integer, ForeignKey("Categoria.Id"), nullable=False)
    Nombre_SubCategoria: Mapped[str] = mapped_column(String(200), nullable=False)
    Timestamp: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    categoria = relationship("Categoria", back_populates="subcategorias")

    __table_args__ = (
        Index("IX_subcat_user_cat", "Id_usuario", "Id_Categoria"),
    )
