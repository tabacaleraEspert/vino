from pydantic import BaseModel, Field


class ReglaCreate(BaseModel):
    patron: str = Field(min_length=1, max_length=120)
    id_categoria: int | None = None
    id_subcategoria: int
    prioridad: int = 100
    confianza: str = "MANUAL"


class ReglaUpdate(BaseModel):
    patron: str | None = Field(default=None, max_length=120)
    id_categoria: int | None = None
    id_subcategoria: int | None = None
    prioridad: int | None = None
    activa: bool | None = None


class ReglaResponse(BaseModel):
    id: int
    comercio: str
    categoria_id: int
    categoria_nombre: str = ""
    subcategoria_id: int
    subcategoria_nombre: str = ""
    prioridad: int = 100
    activa: bool = True
    confianza: str = "AUTO"
    timestamp: str = ""

    model_config = {"from_attributes": True}
