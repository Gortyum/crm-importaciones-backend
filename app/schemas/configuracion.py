from pydantic import BaseModel


class ConfigItem(BaseModel):
    clave: str
    valor: float
    etiqueta: str = ""


class ConfigOut(BaseModel):
    iva_chile: float
    arancel_general: float
    arancel_mercosur: float


class ConfigUpdate(BaseModel):
    iva_chile: float | None = None
    arancel_general: float | None = None
    arancel_mercosur: float | None = None


class ConfigPublic(BaseModel):
    valores: list[ConfigItem]