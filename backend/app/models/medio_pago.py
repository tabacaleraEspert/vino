"""Modelos ORM para catálogo de medios de pago."""
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CardFundingType(Base):
    __tablename__ = "md_card_funding_type"

    card_funding_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class PaymentMethodCatalog(Base):
    __tablename__ = "md_payment_method_catalog"

    id_medio_de_pago_final: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_funding_type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    medio_de_pago_final: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
