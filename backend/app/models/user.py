from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "MaestroUsuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    Nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    Apellido: Mapped[str | None] = mapped_column(String(100))
    # Apodo: Mapped[str | None] = mapped_column(String(50))  # TODO: run migration 015 first
    WppEntero: Mapped[str | None] = mapped_column(String(50))
    Whatsapp: Mapped[str | None] = mapped_column(String(50))
    gmail: Mapped[str | None] = mapped_column(String(255))
    ID_Sheets: Mapped[str | None] = mapped_column(String(500))
    PasswordHash: Mapped[str | None] = mapped_column(String(255))
    OnboardingCompletado: Mapped[bool] = mapped_column(Boolean, server_default="0")
    OnboardingCompletadoAt: Mapped[datetime | None] = mapped_column(DateTime)
    OnboardingStep: Mapped[int | None] = mapped_column(Integer, server_default="0")
    GmailRefreshToken: Mapped[str | None] = mapped_column(String(500))
    GmailConnectedAt: Mapped[datetime | None] = mapped_column(DateTime)
    GmailLastPolledAt: Mapped[datetime | None] = mapped_column(DateTime)
    GmailLastMessageId: Mapped[str | None] = mapped_column(String(100))
    WppOtpCode: Mapped[str | None] = mapped_column(String(10))
    WppOtpExpiresAt: Mapped[datetime | None] = mapped_column(DateTime)
    WppOtpPhone: Mapped[str | None] = mapped_column(String(50))
    CreatedAt: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    UpdatedAt: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    categorias = relationship("Categoria", back_populates="usuario", lazy="selectin")
    movimientos = relationship("Movimiento", back_populates="usuario", lazy="noload")

    __table_args__ = (
        Index("IX_MaestroUsuarios_Nombre", "Nombre"),
    )
