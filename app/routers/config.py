from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.configuracion import ConfigGlobal
from app.schemas.configuracion import ConfigOut, ConfigUpdate
from app.services.config_service import get_config, ensure_config

router = APIRouter(prefix="/api/config", tags=["configuracion"])


@router.get("/", response_model=ConfigOut)
def obtener_config(db: Session = Depends(get_db)):
    ensure_config(db)
    return get_config(db)


@router.put("/", response_model=ConfigOut)
def actualizar_config(data: ConfigUpdate, db: Session = Depends(get_db)):
    ensure_config(db)
    cambios = {
        "IVA_CHILE": data.iva_chile,
        "ARANCEL_GENERAL": data.arancel_general,
        "ARANCEL_MERCOSUR": data.arancel_mercosur,
    }
    for clave, valor in cambios.items():
        if valor is not None:
            row = db.query(ConfigGlobal).filter(ConfigGlobal.clave == clave).first()
            row.valor = valor
    db.commit()
    return get_config(db)