from decimal import Decimal

from pydantic import BaseModel, Field


class PresupuestoCreate(BaseModel):
    mes_anio: str | None = None
    categoria_id: int | None = None
    subcategoria_id: int | None = None
    monto: Decimal = Field(ge=0)


class PresupuestoUpdate(BaseModel):
    monto: Decimal | None = Field(default=None, ge=0)
    categoria_id: int | None = None
    subcategoria_id: int | None = None


class PresupuestoResponse(BaseModel):
    id: int
    mes_anio: str
    categoria_id: str = ""
    categoria_nombre: str = ""
    subcategoria_id: str = ""
    subcategoria_nombre: str = ""
    monto: float

    model_config = {"from_attributes": True}
