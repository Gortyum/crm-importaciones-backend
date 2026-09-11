from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orden_compra import OrdenCompra, ItemOrdenCompra
from app.models.cotizacion import Cotizacion, ItemCotizacion
from app.models.proveedor import Proveedor
from app.schemas.orden_compra import (
    OrdenCompraCreate,
    OrdenCompraOut,
    OrdenCompraPDFData,
    ItemOrdenCompraPDF,
)

router = APIRouter(prefix="/api/ordenes-compra", tags=["ordenes-compra"])

ESTADOS_OC = ["Pendiente", "Confirmada", "En Produccion", "Recibida", "Cancelada"]


def generar_correlativo_oc(db: Session) -> str:
    anio = datetime.now().year
    ultimo = db.query(OrdenCompra).filter(
        OrdenCompra.correlativo.like(f"OC-{anio}-%")
    ).order_by(OrdenCompra.id.desc()).first()
    if ultimo:
        num = int(ultimo.correlativo.split("-")[-1]) + 1
    else:
        num = 1
    return f"OC-{anio}-{num:04d}"


@router.get("/", response_model=list[OrdenCompraOut])
def listar_ordenes(db: Session = Depends(get_db)):
    ordenes = db.query(OrdenCompra).order_by(OrdenCompra.created_at.desc()).all()
    result = []
    for oc in ordenes:
        prov = db.query(Proveedor).get(oc.proveedor_id)
        total = sum(i.subtotal for i in oc.items)
        out = OrdenCompraOut.model_validate(oc)
        out.proveedor_nombre = prov.razon_social if prov else ""
        out.total_general = total
        result.append(out)
    return result


@router.get("/{oc_id}", response_model=OrdenCompraOut)
def obtener_orden(oc_id: int, db: Session = Depends(get_db)):
    oc = db.query(OrdenCompra).get(oc_id)
    if not oc:
        raise HTTPException(404, "Orden de compra no encontrada")
    prov = db.query(Proveedor).get(oc.proveedor_id)
    total = sum(i.subtotal for i in oc.items)
    out = OrdenCompraOut.model_validate(oc)
    out.proveedor_nombre = prov.razon_social if prov else ""
    out.total_general = total
    return out


@router.post("/", response_model=OrdenCompraOut, status_code=201)
def crear_desde_cotizacion(data: OrdenCompraCreate, db: Session = Depends(get_db)):
    cot = db.query(Cotizacion).get(data.cotizacion_id)
    if not cot:
        raise HTTPException(400, "Cotización no encontrada")

    proveedor = db.query(Proveedor).get(data.proveedor_id)
    if not proveedor:
        raise HTTPException(400, "Proveedor no encontrado")

    items_cot = db.query(ItemCotizacion).filter(
        ItemCotizacion.cotizacion_id == cot.id,
        ItemCotizacion.proveedor_id == data.proveedor_id,
    ).all()

    if not items_cot:
        raise HTTPException(400, "No hay items de este proveedor en la cotización")

    correlativo = generar_correlativo_oc(db)
    oc = OrdenCompra(
        correlativo=correlativo,
        cotizacion_id=cot.id,
        proveedor_id=data.proveedor_id,
        notas=data.notas,
        estado="Pendiente",
    )
    db.add(oc)
    db.flush()

    for item_cot in items_cot:
        costo_unit = item_cot.costo_original
        divisa_item = item_cot.divisa_origen or "USD"
        subtotal = round(costo_unit * item_cot.cantidad, 2)
        item = ItemOrdenCompra(
            orden_id=oc.id,
            producto_id=item_cot.producto_id,
            descripcion=item_cot.descripcion,
            cantidad=item_cot.cantidad,
            costo_unitario=round(costo_unit, 2),
            divisa=divisa_item,
            tipo_personalizacion=item_cot.tipo_personalizacion,
            subtotal=subtotal,
        )
        db.add(item)

    db.commit()
    db.refresh(oc)

    total = sum(i.subtotal for i in oc.items)
    out = OrdenCompraOut.model_validate(oc)
    out.proveedor_nombre = proveedor.razon_social
    out.total_general = total
    return out


@router.patch("/{oc_id}/estado")
def cambiar_estado_oc(oc_id: int, estado: str, db: Session = Depends(get_db)):
    oc = db.query(OrdenCompra).get(oc_id)
    if not oc:
        raise HTTPException(404, "Orden de compra no encontrada")
    if estado not in ESTADOS_OC:
        raise HTTPException(400, f"Estado inválido: {estado}")
    oc.estado = estado
    db.commit()
    return {"ok": True, "estado": estado}


@router.get("/{oc_id}/pdf-data", response_model=OrdenCompraPDFData)
def obtener_datos_pdf_oc(oc_id: int, db: Session = Depends(get_db)):
    oc = db.query(OrdenCompra).get(oc_id)
    if not oc:
        raise HTTPException(404, "Orden de compra no encontrada")

    prov = db.query(Proveedor).get(oc.proveedor_id)
    cot = db.query(Cotizacion).get(oc.cotizacion_id)

    items_pdf = []
    for item in oc.items:
        items_pdf.append(ItemOrdenCompraPDF(
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            costo_unitario=item.costo_unitario,
            divisa=item.divisa,
            tipo_personalizacion=item.tipo_personalizacion,
            subtotal=item.subtotal,
        ))

    total_gral = sum(i.subtotal for i in oc.items)

    return OrdenCompraPDFData(
        correlativo=oc.correlativo,
        fecha=oc.created_at,
        proveedor_nombre=prov.razon_social if prov else "",
        proveedor_tax_id=prov.tax_id if prov else "",
        proveedor_pais=prov.pais_origen if prov else "",
        cotizacion_correlativo=cot.correlativo if cot else "",
        items=items_pdf,
        total_general=total_gral,
        notas=oc.notas,
    )
