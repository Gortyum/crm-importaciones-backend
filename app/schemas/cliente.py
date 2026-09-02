from pydantic import BaseModel
from datetime import datetime


class ClienteBase(BaseModel):
    razon_social: str
    rut: str
    direccion: str = ""
    giro: str = ""


class ClienteCreate(ClienteBase):
    pass


class ClienteOut(ClienteBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactoBase(BaseModel):
    nombre: str
    cargo: str = ""
    email: str = ""
    telefono: str = ""
    es_principal: bool = False


class ContactoCreate(ContactoBase):
    pass


class ContactoOut(ContactoBase):
    id: int
    cliente_id: int

    model_config = {"from_attributes": True}
