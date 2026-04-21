from pydantic import BaseModel, Field


class CategoriaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    icon: str = "📁"
    color: str = "#6b7280"


class CategoriaUpdate(BaseModel):
    nombre: str | None = Field(default=None, max_length=200)
    icon: str | None = None
    color: str | None = None


class CategoriaResponse(BaseModel):
    id: int
    nombre: str
    icon: str = "📁"
    color: str = "#6b7280"

    model_config = {"from_attributes": True}


class SubCategoriaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    categoria_id: int


class SubCategoriaUpdate(BaseModel):
    nombre: str | None = Field(default=None, max_length=200)


class SubCategoriaResponse(BaseModel):
    id: int
    categoria_id: int
    nombre: str

    model_config = {"from_attributes": True}
