from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.proveedor import Proveedor
from app.schemas.proveedor import ProveedorCreate, ProveedorOut

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"])


@router.get("/", response_model=list[ProveedorOut])
def listar_proveedores(db: Session = Depends(get_db)):
    return db.query(Proveedor).order_by(Proveedor.razon_social).all()


@router.get("/{proveedor_id}", response_model=ProveedorOut)
def obtener_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    prov = db.query(Proveedor).get(proveedor_id)
    if not prov:
        raise HTTPException(404, "Proveedor no encontrado")
    return prov


@router.post("/", response_model=ProveedorOut, status_code=201)
def crear_proveedor(data: ProveedorCreate, db: Session = Depends(get_db)):
    existente = db.query(Proveedor).filter(Proveedor.tax_id == data.tax_id).first()
    if existente:
        raise HTTPException(400, "Ya existe un proveedor con ese TAX ID")
    prov = Proveedor(**data.model_dump())
    db.add(prov)
    db.commit()
    db.refresh(prov)
    return prov


@router.put("/{proveedor_id}", response_model=ProveedorOut)
def actualizar_proveedor(proveedor_id: int, data: ProveedorCreate, db: Session = Depends(get_db)):
    prov = db.query(Proveedor).get(proveedor_id)
    if not prov:
        raise HTTPException(404, "Proveedor no encontrado")
    for k, v in data.model_dump().items():
        setattr(prov, k, v)
    db.commit()
    db.refresh(prov)
    return prov


@router.delete("/{proveedor_id}", status_code=204)
def eliminar_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    prov = db.query(Proveedor).get(proveedor_id)
    if not prov:
        raise HTTPException(404, "Proveedor no encontrado")
    db.delete(prov)
    db.commit()
