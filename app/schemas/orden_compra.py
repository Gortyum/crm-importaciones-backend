from pydantic import BaseModel
from datetime import datetime


class ItemOrdenCompraBase(BaseModel):
    producto_id: int | None = None
    descripcion: str = ""
    cantidad: int = 1
    costo_unitario: float = 0
    divisa: str = "CLP"
    tipo_personalizacion: str = "Serigrafia"
    subtotal: float = 0
    notas: str = ""


class ItemOrdenCompraOut(ItemOrdenCompraBase):
    id: int
    orden_id: int

    model_config = {"from_attributes": True}


class ItemOrdenCompraPDF(BaseModel):
    descripcion: str
    cantidad: int
    costo_unitario: float
    divisa: str
    tipo_personalizacion: str
    subtotal: float


class OrdenCompraCreate(BaseModel):
    cotizacion_id: int
    proveedor_id: int
    notas: str = ""


class OrdenCompraOut(BaseModel):
    id: int
    correlativo: str
    cotizacion_id: int
    proveedor_id: int
    proveedor_nombre: str = ""
    estado: str
    notas: str
    items: list[ItemOrdenCompraOut] = []
    total_general: float = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class OrdenCompraPDFData(BaseModel):
    correlativo: str
    fecha: datetime
    proveedor_nombre: str
    proveedor_tax_id: str
    proveedor_pais: str
    cotizacion_correlativo: str
    items: list[ItemOrdenCompraPDF] = []
    total_general: float = 0
    notas: str = ""
