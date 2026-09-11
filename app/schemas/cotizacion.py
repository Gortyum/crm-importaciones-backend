from pydantic import BaseModel
from datetime import datetime


class ItemCotizacionBase(BaseModel):
    producto_id: int | None = None
    proveedor_id: int | None = None
    descripcion: str = ""
    cantidad: int = 1
    costo_original: float = 0
    divisa_origen: str = "CLP"
    tipo_cambio: float = 1.0
    peso_kg: float = 0
    volumen_m3: float = 0
    tipo_flete: str = "Terrestre"
    costo_flete: float = 0
    costo_envio: float = 0
    imagen_url: str = ""
    margen_pct: float = 30
    descuento_pct: float = 0
    tipo_personalizacion: str = "Serigrafia"
    iva_pct: float = 19


class ItemCotizacionCreate(ItemCotizacionBase):
    pass


class ItemCotizacionOut(ItemCotizacionBase):
    id: int
    cotizacion_id: int
    precio_venta_unitario: float
    subtotal: float
    iva_monto: float
    total: float

    model_config = {"from_attributes": True}


class ItemCotizacionPDF(BaseModel):
    descripcion: str
    cantidad: int
    divisa_origen: str
    imagen_url: str = ""
    precio_venta_unitario: float
    tipo_personalizacion: str
    subtotal: float
    iva_monto: float
    total: float


class ImportacionCostoCotizacion(BaseModel):
    proveedor_id: int | None = None
    categoria: str = "otro"
    tipo_costo: str = "otro"
    monto: float = 0
    divisa: str = "USD"
    notas: str = ""


class CotizacionImportacion(BaseModel):
    """Datos de la importación que se desea crear junto con la cotización."""
    transporte: str = "Aereo"
    cert_origen: bool = True
    tc_usd_clp: float | None = None
    tc_brl_usd: float = 0.18
    contingencia_pct: float = 2
    costos: list[ImportacionCostoCotizacion] = []


class CotizacionBase(BaseModel):
    cliente_id: int
    contacto_id: int | None = None
    divisa_original: str = "CLP"
    tipo_cambio: float = 1.0
    notas: str = ""
    importacion_id: int | None = None


class CotizacionCreate(CotizacionBase):
    items: list[ItemCotizacionCreate] = []
    importacion: CotizacionImportacion | None = None


class CotizacionUpdateEstado(BaseModel):
    estado: str


class CotizacionOut(CotizacionBase):
    id: int
    correlativo: str
    estado: str
    fecha: datetime
    importacion_correlativo: str = ""
    items: list[ItemCotizacionOut] = []
    total_general: float = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CotizacionPDFData(BaseModel):
    correlativo: str
    fecha: datetime
    cliente_razon_social: str
    cliente_rut: str
    cliente_direccion: str
    contacto_nombre: str = ""
    contacto_email: str = ""
    items: list[ItemCotizacionPDF] = []
    subtotal_general: float = 0
    iva_general: float = 0
    total_general: float = 0
    notas: str = ""
