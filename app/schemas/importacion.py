from pydantic import BaseModel
from datetime import datetime


class ImportacionItemCreate(BaseModel):
    producto_id: int | None = None
    descripcion: str = ""
    cantidad: int = 1
    precio_unitario_fabrica: float = 0
    divisa: str = "USD"
    margen_pct: float = 35


class ImportacionCostoCreate(BaseModel):
    proveedor_id: int | None = None
    categoria: str = ""
    tipo_costo: str = "otro"
    monto: float = 0
    divisa: str = "USD"
    notas: str = ""


class ImportacionProveedorCreate(BaseModel):
    proveedor_id: int
    categoria_id: int | None = None


class ImportacionCreate(BaseModel):
    transporte: str = "Aereo"
    cert_origen: bool = True
    tc_usd_clp: float = 920.0
    tc_brl_usd: float = 0.18
    contingencia_pct: float = 2
    notas: str = ""
    cotizacion_id: int | None = None
    items: list[ImportacionItemCreate] = []
    costos: list[ImportacionCostoCreate] = []
    proveedores: list[ImportacionProveedorCreate] = []


class ImportacionUpdateEstado(BaseModel):
    estado: str


class ImportacionOut(BaseModel):
    id: int
    correlativo: str
    estado: str
    transporte: str
    cert_origen: bool
    tc_usd_clp: float
    tc_brl_usd: float
    contingencia_pct: float
    notas: str
    cotizacion_id: int | None = None
    cotizacion_correlativo: str = ""
    fecha: datetime
    historial_estados: list | None = None
    items: list = []
    costos: list = []
    proveedores: list = []
    resultado: dict | None = None

    model_config = {"from_attributes": True}