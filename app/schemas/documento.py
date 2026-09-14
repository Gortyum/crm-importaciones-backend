from datetime import datetime

from pydantic import BaseModel


class DocumentoEspecificaciones(BaseModel):
    material: str = ""
    personalizacion: str = ""
    color: str = ""
    medida_logo: str = ""


class DocumentoProductoPDF(BaseModel):
    descripcion: str
    cantidad: int
    imagen_url: str = ""


class DocumentoCreate(BaseModel):
    cotizacion_id: int
    especificaciones: DocumentoEspecificaciones = DocumentoEspecificaciones()


class DocumentoOut(BaseModel):
    id: int
    correlativo: str
    cotizacion_id: int
    cotizacion_correlativo: str = ""
    cliente_razon_social: str = ""
    fecha: datetime | None = None
    cantidad_total: int = 0
    productos: list[DocumentoProductoPDF] = []
    especificaciones: DocumentoEspecificaciones | None = None
    created_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentoPDFData(BaseModel):
    correlativo: str
    fecha: datetime | None = None
    cliente_razon_social: str = ""
    cotizacion_correlativo: str = ""
    productos: list[DocumentoProductoPDF] = []
    cantidad_total: int = 0
    especificaciones: DocumentoEspecificaciones | None = None