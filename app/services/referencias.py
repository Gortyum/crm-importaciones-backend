"""Datos de referencia cargados al iniciar sesión.

Incluye únicamente los catálogos que existen hoy en el sistema:
monedas/tipo de cambio, configuración global, estados y transiciones,
categorías de productos y datos del usuario con sus permisos mínimos.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.models.proveedor import ProveedorCategoria
from app.routers.importaciones import (
    ESTADOS_VALIDOS as ESTADOS_IMPORTACION,
    TRANSICIONES as TRANSICIONES_IMPORTACION,
)
from app.routers.cotizaciones import (
    ESTADOS_VALIDOS as ESTADOS_COTIZACION,
    transiciones_validas,
)
from app.routers.ordenes_compra import ESTADOS_OC
from app.services.config_service import get_config
from app.services.divisa import obtener_tipo_cambio

# Permisos por rol. Hoy solo existe administrador por defecto.
PERMISOS_ADMIN = [
    "clientes",
    "proveedores",
    "productos",
    "cotizaciones",
    "importaciones",
    "ordenes_compra",
    "config",
    "usuarios",
]


async def construir_referencias(db: Session, usuario) -> dict:
    rates = await obtener_tipo_cambio()
    config = get_config(db)

    seguridad_pct: float = config.get("contingencia_pct", 2.0)
    factor = 1 + seguridad_pct / 100
    tc_cotizacion = {divisa: round(valor * factor, 2) for divisa, valor in rates.items()}

    categorias = [
        {"id": c.id, "nombre": c.nombre}
        for c in db.query(ProveedorCategoria).order_by(ProveedorCategoria.nombre).all()
    ]

    rol = getattr(usuario, "rol", "admin") or "admin"
    permisos = PERMISOS_ADMIN if rol == "admin" else []

    return {
        "usuario": {"id": usuario.id, "username": usuario.username, "rol": rol},
        "permisos": permisos,
        "monedas": {**rates, "CLP": 1.0},
        "tc_cotizacion": tc_cotizacion,
        "seguridad_pct": seguridad_pct,
        "config": {
            k: config.get(k)
            for k in ("iva_chile", "arancel_general", "arancel_mercosur")
        },
        "estados": {
            "cotizacion": {
                "estados": ESTADOS_COTIZACION,
                "transiciones": {
                    estado: transiciones_validas(estado) for estado in ESTADOS_COTIZACION
                },
            },
            "importacion": {
                "estados": ESTADOS_IMPORTACION,
                "transiciones": TRANSICIONES_IMPORTACION,
            },
            "orden_compra": {"estados": ESTADOS_OC},
        },
        "categorias_productos": categorias,
        "fecha_tc": date.today().isoformat(),
    }