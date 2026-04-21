from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class MovimientoCreate(BaseModel):
    Fecha: date
    MedioCarga: str = "manual"
    TipoMovimiento: Literal["Gasto", "Ingreso"] = "Gasto"
    Moneda: str = Field(default="ARS", max_length=10)
    Monto: Decimal = Field(ge=0)
    Descripcion: str | None = None
    Id_Categoria: int | None = None
    Id_SubCategoria: int | None = None
    ComercioId: str | None = None
    Comercio: str | None = None


class MovimientoUpdate(BaseModel):
    Fecha: date | None = None
    TipoMovimiento: Literal["Gasto", "Ingreso"] | None = None
    Moneda: str | None = None
    Monto: Decimal | None = Field(default=None, ge=0)
    Descripcion: str | None = None
    Id_Categoria: int | None = None
    Id_SubCategoria: int | None = None
    ComercioId: str | None = None


class MovimientoResponse(BaseModel):
    id: str
    fecha: str
    timestamp: str = ""
    tipo: str
    moneda: str = "ARS"
    monto: float
    descripcion: str = ""
    categoria: str = ""
    categoria_id: str = ""
    subcategoria: str = ""
    subcategoria_id: str = ""
    comercio: str = ""
    comercio_id: str = ""
    medio_carga: str = ""

    model_config = {"from_attributes": True}


class MovimientoListResponse(BaseModel):
    items: list[dict]
    page: int
    limit: int
    total: int
