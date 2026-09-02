from pydantic import BaseModel
from datetime import datetime


class ProveedorCategoriaBase(BaseModel):
    nombre: str


class ProveedorCategoriaCreate(ProveedorCategoriaBase):
    pass


class ProveedorCategoriaOut(ProveedorCategoriaBase):
    id: int

    model_config = {"from_attributes": True}


class ProveedorBase(BaseModel):
    razon_social: str
    tax_id: str
    pais_origen: str = ""
    etiquetas_productos: list[str] = []
    categoria_id: int | None = None


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorOut(ProveedorBase):
    id: int
    created_at: datetime
    categoria: ProveedorCategoriaOut | None = None

    model_config = {"from_attributes": True}