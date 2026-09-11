from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.divisa import obtener_tipo_cambio
from app.services.config_service import get_config

router = APIRouter(prefix="/api/divisas", tags=["divisas"])

# Margen de seguridad cambiaria por defecto (porcentaje sobre el TC observado).
# Se usa si la configuración global no define un valor explícito.
SEGURIDAD_DEFAULT_PCT = 2.0


@router.get("/cambio")
async def tipo_cambio(db: Session = Depends(get_db)):
    rates = await obtener_tipo_cambio()
    config = get_config(db)

    # El margen de seguridad reutiliza contingencia_pct de la config global.
    # Esto evita duplicar parámetros de negocio.
    seguridad_pct: float = config.get("contingencia_pct", SEGURIDAD_DEFAULT_PCT)

    # Calculamos el TC de cotización para cada divisa disponible.
    factor = 1 + seguridad_pct / 100
    tc_cotizacion = {divisa: round(valor * factor, 2) for divisa, valor in rates.items()}

    return {
        "monedas": rates,
        "seguridad_pct": seguridad_pct,
        "tc_cotizacion": tc_cotizacion,
        "fecha_tc": date.today().isoformat(),
    }
