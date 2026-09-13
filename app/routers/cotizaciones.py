from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cotizacion import Cotizacion, ItemCotizacion
from app.models.cliente import Cliente, Contacto
from app.models.importacion import Importacion, ImportacionItem, ImportacionProveedor
from app.schemas.cotizacion import (
    CotizacionCreate,
    CotizacionUpdate,
    CotizacionOut,
    CotizacionUpdateEstado,
    CotizacionPDFData,
    ItemCotizacionPDF,
    CotizacionImportacion,
)
from app.services.cotizacion_engine import calcular_item

router = APIRouter(prefix="/api/cotizaciones", tags=["cotizaciones"])

ESTADOS_VALIDOS = ["Creada", "Enviada", "Cerrada", "En Produccion", "Entregada", "Cancelada"]

TRANSICIONES = {
    "Creada": ["Enviada", "Cancelada"],
    "Enviada": ["Cerrada", "Cancelada"],
    "Cerrada": ["En Produccion", "Cancelada"],
    "En Produccion": ["Entregada", "Cancelada"],
    "Entregada": [],
    "Cancelada": [],
}


def generar_correlativo(db: Session) -> str:
    now = datetime.now()
    anio = now.year
    mes = now.month
    ultimo = db.query(Cotizacion).filter(
        Cotizacion.correlativo.like(f"COT-{anio}-{mes:02d}-%")
    ).order_by(Cotizacion.id.desc()).first()
    if ultimo:
        num = int(ultimo.correlativo.split("-")[-1]) + 1
    else:
        num = 1
    return f"COT-{anio}-{mes:02d}-{num:04d}"


def _total_cotizacion(cot) -> float:
    return sum(i.total for i in cot.items)


def _completar_out(cot, db) -> CotizacionOut:
    out = CotizacionOut.model_validate(cot)
    out.total_general = _total_cotizacion(cot)
    out.cliente = db.query(Cliente).get(cot.cliente_id)
    if cot.contacto_id:
        out.contacto = db.query(Contacto).get(cot.contacto_id)
    if cot.importacion_id:
        imp = db.query(Importacion).get(cot.importacion_id)
        out.importacion_correlativo = imp.correlativo if imp else ""
    return out


@router.get("/", response_model=list[CotizacionOut])
def listar_cotizaciones(db: Session = Depends(get_db)):
    cotizaciones = db.query(Cotizacion).order_by(Cotizacion.created_at.desc()).all()
    return [_completar_out(c, db) for c in cotizaciones]


@router.get("/{cotizacion_id}", response_model=CotizacionOut)
def obtener_cotizacion(cotizacion_id: int, db: Session = Depends(get_db)):
    cot = db.query(Cotizacion).get(cotizacion_id)
    if not cot:
        raise HTTPException(404, "Cotización no encontrada")
    return _completar_out(cot, db)


@router.post("/", response_model=CotizacionOut, status_code=201)
async def crear_cotizacion(data: CotizacionCreate, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).get(data.cliente_id)
    if not cliente:
        raise HTTPException(400, "Cliente no encontrado")

    correlativo = generar_correlativo(db)
    cot = Cotizacion(
        correlativo=correlativo,
        cliente_id=data.cliente_id,
        contacto_id=data.contacto_id,
        divisa_original=data.divisa_original,
        tipo_cambio=data.tipo_cambio,
        notas=data.notas,
        importacion_id=data.importacion_id,
        estado="Creada",
        historial_estados=[{"estado": "Creada", "fecha": datetime.now().isoformat()}],
    )
    db.add(cot)
    db.flush()

    for item_data in data.items:
        calc = calcular_item(item_data)
        item = ItemCotizacion(
            cotizacion_id=cot.id,
            producto_id=item_data.producto_id,
            proveedor_id=item_data.proveedor_id,
            descripcion=item_data.descripcion,
            cantidad=item_data.cantidad,
            costo_original=item_data.costo_original,
            divisa_origen=item_data.divisa_origen,
            tipo_cambio=item_data.tipo_cambio,
            peso_kg=item_data.peso_kg,
            volumen_m3=item_data.volumen_m3,
            tipo_flete=item_data.tipo_flete,
            costo_flete=calc["costo_flete"],
            costo_envio=item_data.costo_envio,
            imagen_url=item_data.imagen_url,
            margen_pct=item_data.margen_pct,
            descuento_pct=item_data.descuento_pct,
            tipo_personalizacion=item_data.tipo_personalizacion,
            iva_pct=item_data.iva_pct,
            precio_venta_unitario=calc["precio_venta_unitario"],
            subtotal=calc["subtotal"],
            iva_monto=calc["iva_monto"],
            total=calc["total"],
        )
        db.add(item)

    db.commit()
    db.refresh(cot)

    if data.importacion:
        await _crear_importacion_desde_cotizacion(db, cot, data.importacion)
        db.refresh(cot)

    return _completar_out(cot, db)


@router.put("/{cotizacion_id}", response_model=CotizacionOut)
def actualizar_cotizacion(cotizacion_id: int, data: CotizacionUpdate, db: Session = Depends(get_db)):
    cot = db.query(Cotizacion).get(cotizacion_id)
    if not cot:
        raise HTTPException(404, "Cotización no encontrada")
    if cot.pdf_emitido:
        raise HTTPException(
            409,
            "Esta cotización ya generó su PDF: no se puede editar. Ajusta en la app." ,
        )

    cliente = db.query(Cliente).get(data.cliente_id)
    if not cliente:
        raise HTTPException(400, "Cliente no encontrado")

    cot.cliente_id = data.cliente_id
    cot.contacto_id = data.contacto_id
    cot.divisa_original = data.divisa_original
    cot.tipo_cambio = data.tipo_cambio
    cot.notas = data.notas

    db.query(ItemCotizacion).filter(ItemCotizacion.cotizacion_id == cot.id).delete()
    for item_data in data.items:
        calc = calcular_item(item_data)
        db.add(ItemCotizacion(
            cotizacion_id=cot.id,
            producto_id=item_data.producto_id,
            proveedor_id=item_data.proveedor_id,
            descripcion=item_data.descripcion,
            cantidad=item_data.cantidad,
            costo_original=item_data.costo_original,
            divisa_origen=item_data.divisa_origen,
            tipo_cambio=item_data.tipo_cambio,
            peso_kg=item_data.peso_kg,
            volumen_m3=item_data.volumen_m3,
            tipo_flete=item_data.tipo_flete,
            costo_flete=calc["costo_flete"],
            costo_envio=item_data.costo_envio,
            imagen_url=item_data.imagen_url,
            margen_pct=item_data.margen_pct,
            descuento_pct=item_data.descuento_pct,
            tipo_personalizacion=item_data.tipo_personalizacion,
            iva_pct=item_data.iva_pct,
            precio_venta_unitario=calc["precio_venta_unitario"],
            subtotal=calc["subtotal"],
            iva_monto=calc["iva_monto"],
            total=calc["total"],
        ))

    db.commit()
    db.refresh(cot)
    return _completar_out(cot, db)


@router.patch("/{cotizacion_id}/estado", response_model=CotizacionOut)
def cambiar_estado(cotizacion_id: int, data: CotizacionUpdateEstado, db: Session = Depends(get_db)):
    cot = db.query(Cotizacion).get(cotizacion_id)
    if not cot:
        raise HTTPException(404, "Cotización no encontrada")

    if data.estado not in ESTADOS_VALIDOS:
        raise HTTPException(400, f"Estado inválido: {data.estado}")

    permitidos = TRANSICIONES.get(cot.estado, [])
    if data.estado not in permitidos:
        raise HTTPException(
            400,
            f"No se puede cambiar de '{cot.estado}' a '{data.estado}'. Transiciones válidas: {permitidos}",
        )

    historial = cot.historial_estados or []
    historial.append({"estado": data.estado, "fecha": datetime.now().isoformat()})
    cot.estado = data.estado
    cot.historial_estados = historial

    db.commit()
    db.refresh(cot)
    return _completar_out(cot, db)


async def _crear_importacion_desde_cotizacion(
    db: Session,
    cot: Cotizacion,
    importacion_data: CotizacionImportacion | None = None,
) -> Importacion:
    """Crea y vincula una importación de costeo a partir de los items de la cotización."""
    from app.routers.importaciones import (
        generar_correlativo as gen_imp,
        _guardar_calculos,
        _serializar,
        Importacion,
        ImportacionItem,
        ImportacionCosto,
        ImportacionProveedor,
    )
    from app.schemas.importacion import ImportacionItemCreate
    from app.services.divisa import obtener_tipo_cambio

    importacion_data = importacion_data or CotizacionImportacion()

    items = [
        ImportacionItemCreate(
            producto_id=item.producto_id,
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario_fabrica=item.costo_original,
            divisa=item.divisa_origen,
            margen_pct=item.margen_pct,
        )
        for item in cot.items
    ]

    # Tipo de cambio USD->CLP: si la cotización está en USD se respeta el tipo de
    # cambio definido por el usuario; en otro caso se usa la tasa de mercado real.
    if importacion_data.tc_usd_clp and importacion_data.tc_usd_clp > 0:
        tc_usd_clp = importacion_data.tc_usd_clp
    else:
        tasas = await obtener_tipo_cambio()
        if cot.divisa_original.upper() == "USD" and cot.tipo_cambio > 0:
            tc_usd_clp = cot.tipo_cambio
        else:
            tc_usd_clp = tasas.get("USD") or cot.tipo_cambio or 950.0

    tc_brl_usd = importacion_data.tc_brl_usd if importacion_data.tc_brl_usd else 0.18

    desde = Importacion(
        correlativo=gen_imp(db),
        transporte=importacion_data.transporte or "Aereo",
        cert_origen=importacion_data.cert_origen,
        tc_usd_clp=tc_usd_clp,
        tc_brl_usd=tc_brl_usd,
        contingencia_pct=importacion_data.contingencia_pct,
        notas=f"Generada desde cotización {cot.correlativo}",
        cotizacion_id=cot.id,
        estado="Borrador",
        historial_estados=[{"estado": "Borrador", "fecha": datetime.now().isoformat()}],
    )
    db.add(desde)
    db.flush()
    for it in items:
        db.add(ImportacionItem(importacion_id=desde.id, **it.model_dump()))
    for c in importacion_data.costos:
        db.add(ImportacionCosto(importacion_id=desde.id, **c.model_dump()))
    proveedor_ids = {it.proveedor_id for it in cot.items if it.proveedor_id}
    for pid in proveedor_ids:
        db.add(ImportacionProveedor(importacion_id=desde.id, proveedor_id=pid))
    cot.importacion_id = desde.id
    db.commit()
    db.refresh(desde)
    _guardar_calculos(desde, db)
    return _serializar(desde, db)


@router.post("/{cotizacion_id}/crear-importacion")
async def crear_importacion_desde_cot(cotizacion_id: int, db: Session = Depends(get_db)):
    cot = db.query(Cotizacion).get(cotizacion_id)
    if not cot:
        raise HTTPException(404, "Cotización no encontrada")
    if cot.importacion_id:
        raise HTTPException(400, "Esta cotización ya está vinculada a una importación")

    return await _crear_importacion_desde_cotizacion(db, cot)


@router.get("/{cotizacion_id}/pdf-data", response_model=CotizacionPDFData)
def obtener_datos_pdf(cotizacion_id: int, db: Session = Depends(get_db)):
    cot = db.query(Cotizacion).get(cotizacion_id)
    if not cot:
        raise HTTPException(404, "Cotización no encontrada")

    if not cot.pdf_emitido:
        cot.pdf_emitido = True
        db.commit()
        db.refresh(cot)

    cliente = db.query(Cliente).get(cot.cliente_id)
    contacto = db.query(Contacto).get(cot.contacto_id) if cot.contacto_id else None

    items_pdf = []
    for item in cot.items:
        items_pdf.append(ItemCotizacionPDF(
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            divisa_origen=item.divisa_origen,
            imagen_url=item.imagen_url,
            precio_venta_unitario=item.precio_venta_unitario,
            tipo_personalizacion=item.tipo_personalizacion,
            subtotal=item.subtotal,
            iva_monto=item.iva_monto,
            total=item.total,
        ))

    subtotal_gral = sum(i.subtotal for i in cot.items)
    iva_gral = sum(i.iva_monto for i in cot.items)
    total_gral = sum(i.total for i in cot.items)

    return CotizacionPDFData(
        correlativo=cot.correlativo,
        fecha=cot.fecha,
        cliente_razon_social=cliente.razon_social,
        cliente_rut=cliente.rut,
        cliente_direccion=cliente.direccion,
        contacto_nombre=contacto.nombre if contacto else "",
        contacto_email=contacto.email if contacto else "",
        items=items_pdf,
        subtotal_general=subtotal_gral,
        iva_general=iva_gral,
        total_general=total_gral,
        notas=cot.notas,
    )
