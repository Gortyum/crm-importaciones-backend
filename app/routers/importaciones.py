from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.importacion import (
    Importacion,
    ImportacionItem,
    ImportacionCosto,
    ImportacionProveedor,
)
from app.models.cotizacion import Cotizacion, ItemCotizacion
from app.models.cliente import Cliente
from app.schemas.importacion import (
    ImportacionCreate,
    ImportacionOut,
    ImportacionUpdateEstado,
)
from app.schemas.cotizacion import ItemCotizacionCreate
from app.services.importacion_engine import calcular_importacion
from app.services.config_service import get_config, ensure_config
from app.services.cotizacion_engine import calcular_item
from app.services.correlativos import (
    SERIE_COTIZACION,
    SERIE_IMPORTACION,
    con_correlativo,
    siguiente_correlativo,
)

router = APIRouter(prefix="/api/importaciones", tags=["importaciones"])

ESTADOS_VALIDOS = ["Borrador", "En Transito", "En Bodega", "Cerrada", "Cancelada"]
TRANSICIONES = {
    "Borrador": ["En Transito", "Cancelada"],
    "En Transito": ["En Bodega", "Cancelada"],
    "En Bodega": ["Cerrada", "Cancelada"],
    "Cerrada": [],
    "Cancelada": [],
}


class PasarACotizacionRequest(BaseModel):
    cliente_id: int
    contacto_id: int | None = None


def generar_correlativo(db: Session) -> str:
    """Compatibilidad: cotizaciones importa este helper al crear importaciones."""
    return siguiente_correlativo(db, Importacion, SERIE_IMPORTACION)


def _serializar(imp: Importacion, db: Session) -> ImportacionOut:
    config = get_config(db)
    resultado = calcular_importacion(
        items=[
            {"producto_id": i.producto_id, "descripcion": i.descripcion,
             "cantidad": i.cantidad, "precio_unitario_fabrica": i.precio_unitario_fabrica,
             "divisa": i.divisa, "margen_pct": i.margen_pct}
            for i in imp.items
        ],
        costos=[
            {"monto": c.monto, "divisa": c.divisa, "tipo_costo": c.tipo_costo, "categoria": c.categoria}
            for c in imp.costos
        ],
        tc_usd_clp=imp.tc_usd_clp,
        tc_brl_usd=imp.tc_brl_usd,
        contingencia_pct=imp.contingencia_pct,
        cert_origen=imp.cert_origen,
        arancel_general=config["arancel_general"],
        arancel_mercosur=config["arancel_mercosur"],
        iva_pct=config["iva_chile"],
    )
    cot_correlativo = ""
    if imp.cotizacion_id:
        cot = db.query(Cotizacion).get(imp.cotizacion_id)
        cot_correlativo = cot.correlativo if cot else ""

    return ImportacionOut(
        id=imp.id,
        correlativo=imp.correlativo,
        estado=imp.estado,
        transporte=imp.transporte,
        cert_origen=imp.cert_origen,
        tc_usd_clp=imp.tc_usd_clp,
        tc_brl_usd=imp.tc_brl_usd,
        contingencia_pct=imp.contingencia_pct,
        notas=imp.notas,
        cotizacion_id=imp.cotizacion_id,
        cotizacion_correlativo=cot_correlativo,
        fecha=imp.fecha,
        historial_estados=imp.historial_estados,
        items=[
            {
                "id": i.id,
                "producto_id": i.producto_id,
                "descripcion": i.descripcion,
                "cantidad": i.cantidad,
                "precio_unitario_fabrica": i.precio_unitario_fabrica,
                "divisa": i.divisa,
                "margen_pct": i.margen_pct,
                "costo_fob_usd": i.costo_fob_usd,
                "costo_cif_usd": i.costo_cif_usd,
                "costo_unitario_neto_clp": i.costo_unitario_neto_clp,
                "precio_venta_neto_clp": i.precio_venta_neto_clp,
                "iva_venta_clp": i.iva_venta_clp,
                "precio_venta_total_clp": i.precio_venta_total_clp,
            }
            for i in imp.items
        ],
        costos=[
            {
                "id": c.id,
                "proveedor_id": c.proveedor_id,
                "categoria": c.categoria,
                "tipo_costo": c.tipo_costo,
                "monto": c.monto,
                "divisa": c.divisa,
                "notas": c.notas,
                "proveedor": c.proveedor.razon_social if c.proveedor else "",
            }
            for c in imp.costos
        ],
        proveedores=[
            {
                "id": p.id,
                "proveedor_id": p.proveedor_id,
                "categoria_id": p.categoria_id,
                "razon_social": p.proveedor.razon_social if p.proveedor else "",
                "categoria": p.categoria.nombre if p.categoria else "",
            }
            for p in imp.proveedores
        ],
        resultado=resultado,
    )


def _guardar_calculos(imp: Importacion, db: Session) -> None:
    resultado = _serializar(imp, db).resultado
    for idx, item_db in enumerate(imp.items):
        r = resultado["items"][idx] if idx < len(resultado["items"]) else None
        if r:
            item_db.costo_fob_usd = r["fob_usd"]
            item_db.costo_cif_usd = r["cif_usd"]
            item_db.costo_unitario_neto_clp = r["costo_unitario_neto_clp"]
            item_db.precio_venta_neto_clp = r["precio_venta_neto_clp"]
            item_db.iva_venta_clp = r["iva_venta_clp"]
            item_db.precio_venta_total_clp = r["precio_venta_total_clp"]
    db.commit()


@router.get("/", response_model=list[ImportacionOut])
def listar_importaciones(db: Session = Depends(get_db)):
    importaciones = db.query(Importacion).order_by(Importacion.created_at.desc()).all()
    return [_serializar(imp, db) for imp in importaciones]


@router.get("/{importacion_id}", response_model=ImportacionOut)
def obtener_importacion(importacion_id: int, db: Session = Depends(get_db)):
    imp = db.query(Importacion).get(importacion_id)
    if not imp:
        raise HTTPException(404, "Importación no encontrada")
    return _serializar(imp, db)


@router.post("/", response_model=ImportacionOut, status_code=201)
def crear_importacion(data: ImportacionCreate, db: Session = Depends(get_db)):
    ensure_config(db)

    def construir(correlativo: str) -> Importacion:
        imp = Importacion(
            correlativo=correlativo,
            transporte=data.transporte,
            cert_origen=data.cert_origen,
            tc_usd_clp=data.tc_usd_clp,
            tc_brl_usd=data.tc_brl_usd,
            contingencia_pct=data.contingencia_pct,
            notas=data.notas,
            cotizacion_id=data.cotizacion_id,
            estado="Borrador",
            historial_estados=[{"estado": "Borrador", "fecha": datetime.now().isoformat()}],
        )
        db.add(imp)
        db.flush()

        for it in data.items:
            db.add(ImportacionItem(importacion_id=imp.id, **it.model_dump()))
        for c in data.costos:
            db.add(ImportacionCosto(importacion_id=imp.id, **c.model_dump()))
        for p in data.proveedores:
            db.add(ImportacionProveedor(importacion_id=imp.id, **p.model_dump()))
        return imp

    imp = con_correlativo(db, Importacion, SERIE_IMPORTACION, construir)
    _guardar_calculos(imp, db)
    return _serializar(imp, db)


@router.patch("/{importacion_id}/estado", response_model=ImportacionOut)
def cambiar_estado(importacion_id: int, data: ImportacionUpdateEstado, db: Session = Depends(get_db)):
    imp = db.query(Importacion).get(importacion_id)
    if not imp:
        raise HTTPException(404, "Importación no encontrada")

    if data.estado not in ESTADOS_VALIDOS:
        raise HTTPException(400, f"Estado inválido: {data.estado}")
    permitidos = TRANSICIONES.get(imp.estado, [])
    if data.estado not in permitidos:
        raise HTTPException(
            400,
            f"No se puede cambiar de '{imp.estado}' a '{data.estado}'. Transiciones válidas: {permitidos}",
        )

    historial = list(imp.historial_estados or [])
    historial.append({"estado": data.estado, "fecha": datetime.now().isoformat()})
    imp.estado = data.estado
    imp.historial_estados = historial

    db.commit()
    db.refresh(imp)
    return _serializar(imp, db)


@router.delete("/{importacion_id}", status_code=204)
def eliminar_importacion(importacion_id: int, db: Session = Depends(get_db)):
    imp = db.query(Importacion).get(importacion_id)
    if not imp:
        raise HTTPException(404, "Importación no encontrada")
    if imp.cotizacion_id:
        cot = db.query(Cotizacion).get(imp.cotizacion_id)
        if cot:
            cot.importacion_id = None
    db.delete(imp)
    db.commit()


@router.post("/{importacion_id}/pasar-a-cotizacion", response_model=ImportacionOut)
def pasar_a_cotizacion(importacion_id: int, data: PasarACotizacionRequest, db: Session = Depends(get_db)):
    imp = db.query(Importacion).get(importacion_id)
    if not imp:
        raise HTTPException(404, "Importación no encontrada")
    if imp.cotizacion_id:
        raise HTTPException(400, "Esta importación ya está vinculada a una cotización")

    if not db.query(Cliente).get(data.cliente_id):
        raise HTTPException(400, "Cliente no encontrado")

    resultado = _serializar(imp, db).resultado
    items_res = {i["descripcion"]: i for i in resultado["items"]}

    def construir(correlativo: str) -> Cotizacion:
        cot = Cotizacion(
            correlativo=correlativo,
            cliente_id=data.cliente_id,
            contacto_id=data.contacto_id,
            divisa_original="CLP",
            tipo_cambio=1.0,
            notas=f"Generada desde importación {imp.correlativo}",
            estado="Creada",
            historial_estados=[{"estado": "Creada", "fecha": datetime.now().isoformat()}],
        )
        db.add(cot)
        db.flush()

        for item_db in imp.items:
            r = items_res.get(item_db.descripcion, {})
            costo = item_db.costo_unitario_neto_clp or r.get("costo_unitario_neto_clp", 0)
            target = item_db.precio_venta_neto_clp or r.get("precio_venta_neto_clp", 0)
            margen = (target / costo - 1) * 100 if costo else 0
            dummy = ItemCotizacionCreate(
                cantidad=item_db.cantidad,
                costo_original=costo,
                margen_pct=max(margen, 0),
            )
            calc = calcular_item(dummy)
            db.add(ItemCotizacion(
                cotizacion_id=cot.id,
                producto_id=item_db.producto_id,
                descripcion=item_db.descripcion,
                cantidad=item_db.cantidad,
                costo_original=costo,
                divisa_origen="CLP",
                costo_flete=0,
                costo_envio=0,
                margen_pct=max(margen, 0),
                descuento_pct=0,
                iva_pct=19,
                precio_venta_unitario=calc["precio_venta_unitario"],
                subtotal=calc["subtotal"],
                iva_monto=calc["iva_monto"],
                total=calc["total"],
            ))

        cot.importacion_id = imp.id
        imp.cotizacion_id = cot.id
        return cot

    con_correlativo(db, Cotizacion, SERIE_COTIZACION, construir)
    return _serializar(imp, db)