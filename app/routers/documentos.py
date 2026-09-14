from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cotizacion import Cotizacion
from app.models.documento import Documento
from app.models.usuario import Usuario
from app.routers.auth import obtener_usuario_actual
from app.schemas.documento import (
    DocumentoCreate,
    DocumentoOut,
    DocumentoPDFData,
    DocumentoProductoPDF,
)

router = APIRouter(prefix="/api/documentos", tags=["documentos"])


def generar_correlativo(db: Session) -> str:
    ultimo = (
        db.query(Documento)
        .filter(Documento.correlativo.like("PDF %"))
        .order_by(Documento.id.desc())
        .first()
    )
    if ultimo:
        num = int(ultimo.correlativo.split(" ")[-1]) + 1
    else:
        num = 1
    return f"PDF {num}"


def _productos_de_cot(cot: Cotizacion) -> list[DocumentoProductoPDF]:
    return [
        DocumentoProductoPDF(
            descripcion=item.descripcion or "Item",
            cantidad=item.cantidad or 1,
            imagen_url=item.imagen_url or "",
        )
        for item in (cot.items or [])
    ]


def _armar_out(doc: Documento, db: Session) -> DocumentoOut:
    cot = db.query(Cotizacion).get(doc.cotizacion_id)
    productos = _productos_de_cot(cot) if cot else []
    return DocumentoOut(
        id=doc.id,
        correlativo=doc.correlativo,
        cotizacion_id=doc.cotizacion_id,
        cotizacion_correlativo=cot.correlativo if cot else "",
        cliente_razon_social=cot.cliente.razon_social if cot and cot.cliente else "",
        fecha=cot.fecha if cot else None,
        cantidad_total=sum(p.cantidad for p in productos),
        productos=productos,
        especificaciones=doc.especificaciones,
        created_by=doc.created_by,
        created_at=doc.created_at,
    )


@router.get("/", response_model=list[DocumentoOut])
def listar_documentos(db: Session = Depends(get_db)):
    docs = db.query(Documento).order_by(Documento.created_at.desc()).all()
    return [_armar_out(d, db) for d in docs]


@router.post("/", response_model=DocumentoOut, status_code=201)
def crear_documento(
    data: DocumentoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    cot = db.query(Cotizacion).get(data.cotizacion_id)
    if not cot:
        raise HTTPException(400, "Cotización no encontrada")

    doc = Documento(
        correlativo=generar_correlativo(db),
        cotizacion_id=cot.id,
        especificaciones=data.especificaciones.model_dump() if data.especificaciones else None,
        created_by=usuario.username,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _armar_out(doc, db)


@router.get("/{documento_id}", response_model=DocumentoOut)
def obtener_documento(documento_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).get(documento_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    return _armar_out(doc, db)


@router.get("/{documento_id}/pdf-data", response_model=DocumentoPDFData)
def datos_pdf_documento(documento_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).get(documento_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")

    cot = db.query(Cotizacion).get(doc.cotizacion_id)
    productos = _productos_de_cot(cot) if cot else []
    return DocumentoPDFData(
        correlativo=doc.correlativo,
        fecha=cot.fecha if cot else None,
        cliente_razon_social=cot.cliente.razon_social if cot and cot.cliente else "",
        cotizacion_correlativo=cot.correlativo if cot else "",
        productos=productos,
        cantidad_total=sum(p.cantidad for p in productos),
        especificaciones=doc.especificaciones,
    )


@router.delete("/{documento_id}", status_code=204)
def eliminar_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    doc = db.query(Documento).get(documento_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    db.delete(doc)
    db.commit()