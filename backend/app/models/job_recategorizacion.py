from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class JobRecategorizacion(Base):
    __tablename__ = "JobRecategorizacion"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("MaestroUsuarios.id"), nullable=False)
    ReglaComercioId: Mapped[int] = mapped_column(Integer, ForeignKey("ReglaComercio.Id"), nullable=False)
    SinceDate: Mapped[date] = mapped_column(Date, nullable=False)
    Status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PENDING")
    UpdatedRows: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    Error: Mapped[str | None] = mapped_column(String(2000))
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("IX_JobRecategorizacion_User_Status", "Id_usuario", "Status", "CreatedAt"),
    )
