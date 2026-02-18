from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, Literal

TipoMovimiento = Literal["GASTO", "INGRESO"]

class MovimientoBase(BaseModel):
    fecha: date
    id_usuario: str
    medio_carga: str | None = None
    tipo_movimiento: TipoMovimiento
    moneda: str = Field(default="ARS", min_length=1)
    monto: float
    medios_pago: str | None = None
    descripcion: str | None = None
    nombre_categoria: str | None = None
    nombre_subcategoria: str | None = None
    comercio: str | None = None

class MovimientoCreate(MovimientoBase):
    pass

class MovimientoUpdate(BaseModel):
    fecha: Optional[date] = None
    moneda: Optional[str] = None
    monto: Optional[float] = None
    medios_pago: Optional[str] = None
    descripcion: Optional[str] = None
    nombre_categoria: Optional[str] = None
    nombre_subcategoria: Optional[str] = None
    comercio: Optional[str] = None

class MovimientoOut(MovimientoBase):
    id: str
    timestamp: datetime | None = None
