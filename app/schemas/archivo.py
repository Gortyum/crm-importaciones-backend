from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArchivoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_original: str
    object_key: str
    carpeta: str
    entidad_tipo: str
    entidad_id: int | None
    mime_type: str
    tamano: int
    es_publico: bool
    created_by: str | None
    created_at: datetime
    url: str | None = None


class ArchivoUploadResult(BaseModel):
    id: int
    nombre_original: str
    object_key: str
    carpeta: str
    entidad_tipo: str
    entidad_id: int | None
    mime_type: str
    tamano: int
    es_publico: bool
    url: str | None = None