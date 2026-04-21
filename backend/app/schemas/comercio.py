from pydantic import BaseModel, Field


class ComercioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    defaultCategoryId: str | None = None
    defaultSubcategoryId: str | None = None


class ComercioUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    defaultCategoryId: str | None = None
    defaultSubcategoryId: str | None = None


class ComercioResponse(BaseModel):
    id: str
    name: str
    defaultCategoryId: str | None = None
    defaultSubcategoryId: str | None = None

    model_config = {"from_attributes": True}
