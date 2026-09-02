from pydantic import BaseModel
from datetime import datetime


class ProductoBase(BaseModel):
    nombre: str
    descripcion: str = ""
    unidad: str = "Unidad"


class ProductoCreate(ProductoBase):
    pass


class ProductoOut(ProductoBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
