import enum


class EstadoCotizacion(str, enum.Enum):
    CREADA = "Creada"
    ENVIADA = "Enviada"
    CERRADA = "Cerrada"
    EN_PRODUCCION = "En Produccion"
    ENTREGADA = "Entregada"
    CANCELADA = "Cancelada"


class TipoFlete(str, enum.Enum):
    AEREO = "Aereo"
    TERRESTRE = "Terrestre"
    MARITIMO = "Maritimo"


class TipoPersonalizacion(str, enum.Enum):
    BORDADO = "Bordado"
    SERIGRAFIA = "Serigrafia"
    FULL_PRINT = "Full Print"
    DTF = "Dtf"
    SUBLIMACION = "Sublimacion"


class TipoEmpresa(str, enum.Enum):
    CLIENTE = "cliente"
    PROVEEDOR = "proveedor"


class Divisa(str, enum.Enum):
    CLP = "CLP"
    USD = "USD"
    BRL = "BRL"
