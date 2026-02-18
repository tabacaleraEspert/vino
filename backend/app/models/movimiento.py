from datetime import date
from typing import Optional

from pydantic import BaseModel


class MovimientoBase(BaseModel):
    fecha: date
    tipo: str  # ingreso | gasto
    monto: float
    moneda: str = "ARS"
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    comercio: Optional[str] = None
    nota: Optional[str] = None


class MovimientoCreate(MovimientoBase):
    pass


class MovimientoUpdate(BaseModel):
    fecha: Optional[date] = None
    tipo: Optional[str] = None
    monto: Optional[float] = None
    moneda: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    comercio: Optional[str] = None
    nota: Optional[str] = None


class MovimientoOut(MovimientoBase):
    id: str

    class Config:
        from_attributes = True
