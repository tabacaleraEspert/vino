"""Modelos ORM para catálogo de medios de pago."""
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CardFundingType(Base):
    __tablename__ = "md_card_funding_type"

    card_funding_type_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class PaymentMethodCatalog(Base):
    __tablename__ = "md_payment_method_catalog"

    id_medio_de_pago_final: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_funding_type_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("md_card_funding_type.card_funding_type_id"), nullable=True
    )
    medio_de_pago_final: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
