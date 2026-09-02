from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.proveedor import ProveedorCategoria, Proveedor
from app.schemas.proveedor import ProveedorCategoriaCreate, ProveedorCategoriaOut

router = APIRouter(prefix="/api/proveedor-categorias", tags=["proveedor-categorias"])


@router.get("/", response_model=list[ProveedorCategoriaOut])
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(ProveedorCategoria).order_by(ProveedorCategoria.nombre).all()


@router.post("/", response_model=ProveedorCategoriaOut, status_code=201)
def crear_categoria(data: ProveedorCategoriaCreate, db: Session = Depends(get_db)):
    existente = db.query(ProveedorCategoria).filter(ProveedorCategoria.nombre == data.nombre).first()
    if existente:
        raise HTTPException(400, "Ya existe una categoría con ese nombre")
    cat = ProveedorCategoria(nombre=data.nombre)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{categoria_id}", response_model=ProveedorCategoriaOut)
def actualizar_categoria(categoria_id: int, data: ProveedorCategoriaCreate, db: Session = Depends(get_db)):
    cat = db.query(ProveedorCategoria).get(categoria_id)
    if not cat:
        raise HTTPException(404, "Categoría no encontrada")
    cat.nombre = data.nombre
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{categoria_id}", status_code=204)
def eliminar_categoria(categoria_id: int, db: Session = Depends(get_db)):
    cat = db.query(ProveedorCategoria).get(categoria_id)
    if not cat:
        raise HTTPException(404, "Categoría no encontrada")
    db.query(Proveedor).filter(Proveedor.categoria_id == categoria_id).update({"categoria_id": None})
    db.delete(cat)
    db.commit()