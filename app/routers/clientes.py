from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cliente import Cliente, Contacto
from app.schemas.cliente import ClienteCreate, ClienteOut, ContactoCreate, ContactoOut

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


@router.get("/", response_model=list[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).order_by(Cliente.razon_social).all()


@router.get("/{cliente_id}", response_model=ClienteOut)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return cliente


@router.post("/", response_model=ClienteOut, status_code=201)
def crear_cliente(data: ClienteCreate, db: Session = Depends(get_db)):
    existente = db.query(Cliente).filter(Cliente.rut == data.rut).first()
    if existente:
        raise HTTPException(400, "Ya existe un cliente con ese RUT")
    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
def actualizar_cliente(cliente_id: int, data: ClienteCreate, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    for k, v in data.model_dump().items():
        setattr(cliente, k, v)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=204)
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    db.delete(cliente)
    db.commit()


@router.get("/{cliente_id}/contactos", response_model=list[ContactoOut])
def listar_contactos(cliente_id: int, db: Session = Depends(get_db)):
    return db.query(Contacto).filter(Contacto.cliente_id == cliente_id).all()


@router.post("/{cliente_id}/contactos", response_model=ContactoOut, status_code=201)
def crear_contacto(cliente_id: int, data: ContactoCreate, db: Session = Depends(get_db)):
    contacto = Contacto(cliente_id=cliente_id, **data.model_dump())
    db.add(contacto)
    db.commit()
    db.refresh(contacto)
    return contacto


@router.delete("/{cliente_id}/contactos/{contacto_id}", status_code=204)
def eliminar_contacto(cliente_id: int, contacto_id: int, db: Session = Depends(get_db)):
    contacto = db.query(Contacto).filter(Contacto.id == contacto_id, Contacto.cliente_id == cliente_id).first()
    if not contacto:
        raise HTTPException(404, "Contacto no encontrado")
    db.delete(contacto)
    db.commit()
