from sqlalchemy.orm import Session

from app.models.configuracion import ConfigGlobal

DEFAULTS = {
    "IVA_CHILE": 19,
    "ARANCEL_GENERAL": 6,
    "ARANCEL_MERCOSUR": 0,
}

CLAVES = ["IVA_CHILE", "ARANCEL_GENERAL", "ARANCEL_MERCOSUR"]


def get_config(db: Session) -> dict:
    rows = {r.clave: r.valor for r in db.query(ConfigGlobal).all()}
    return {c.lower(): rows.get(c, DEFAULTS[c]) for c in CLAVES}


def ensure_config(db: Session) -> None:
    for clave, valor in DEFAULTS.items():
        if not db.query(ConfigGlobal).filter(ConfigGlobal.clave == clave).first():
            db.add(ConfigGlobal(clave=clave, valor=valor, etiqueta=clave))
    db.commit()